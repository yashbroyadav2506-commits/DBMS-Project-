from contextlib import contextmanager
import mysql.connector
from mysql.connector import pooling
from flask import g, session
from config import Config
from logger import logger

class DatabaseUnreachableError(Exception):
    """Raised when the application is unable to reach or connect to the MySQL database."""
    pass

_pools = {}

def get_connection_params(role: str) -> dict:
    """
    Constructs serverless-friendly connection parameters with configurable SSL,
    timeouts, and role credentials.
    """
    if role == 'clerk':
        user = Config.CLERK_DB_USER
        password = Config.CLERK_DB_PASS
    else:
        user = Config.MANAGER_DB_USER
        password = Config.MANAGER_DB_PASS

    params = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': user,
        'password': password,
        'database': Config.DB_NAME,
        'autocommit': False,
        'connection_timeout': Config.DB_CONNECT_TIMEOUT,
    }

    # SSL parameters for Cloud/Hosted MySQL (Aiven, PlanetScale, TiDB Cloud, AWS RDS)
    if Config.DB_SSL_CA:
        params['ssl_ca'] = Config.DB_SSL_CA
    if Config.DB_SSL_DISABLED:
        params['ssl_disabled'] = True
    elif Config.DB_SSL_MODE:
        params['ssl_mode'] = Config.DB_SSL_MODE

    return params

def get_connection_pool(role: str):
    """
    Returns or initializes a connection pool for the specified role ('manager' or 'clerk').
    """
    if role not in _pools:
        params = get_connection_params(role)
        pool_name = f"pool_{role}"

        try:
            _pools[role] = pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=Config.DB_POOL_SIZE,
                pool_reset_session=True,
                **params
            )
            logger.info(f"Initialized MySQL connection pool '{pool_name}' (size={Config.DB_POOL_SIZE}, host={Config.DB_HOST})")
        except mysql.connector.Error as err:
            logger.error(f"Failed to initialize MySQL pool for {role} on {Config.DB_HOST}:{Config.DB_PORT}: {err}")
            raise DatabaseUnreachableError(
                f"Cannot connect to MySQL database at {Config.DB_HOST}:{Config.DB_PORT} ({err}). "
                "Please verify your database host, credentials, SSL, and network accessibility."
            ) from err

    return _pools[role]

def get_db_connection(role: str = None):
    """
    Retrieves a connection from the pool with automatic pre-ping / reconnect on stale sockets.
    Falls back to a direct connection if the pool is exhausted.
    """
    if not role:
        if hasattr(g, 'user') and g.user and 'role' in g.user:
            role = g.user['role']
        elif 'role' in session:
            role = session['role']
        else:
            role = 'manager'

    conn = None
    try:
        pool = get_connection_pool(role)
        conn = pool.get_connection()
    except mysql.connector.PoolError:
        logger.warning(f"Connection pool for '{role}' exhausted, falling back to direct connection.")
        try:
            conn = mysql.connector.connect(**get_connection_params(role))
        except mysql.connector.Error as err:
            raise DatabaseUnreachableError(
                f"Database connection failed for role '{role}' on {Config.DB_HOST}: {err}"
            ) from err
    except DatabaseUnreachableError:
        raise
    except Exception as err:
        logger.error(f"Error acquiring connection from pool: {err}")
        try:
            conn = mysql.connector.connect(**get_connection_params(role))
        except Exception as direct_err:
            raise DatabaseUnreachableError(
                f"Database is unreachable on {Config.DB_HOST}:{Config.DB_PORT}: {direct_err}"
            ) from direct_err

    # Pre-ping validation: Reconnect if connection was dropped by cloud idle timeout
    if conn:
        try:
            conn.ping(reconnect=True, attempts=3, delay=1)
        except Exception as ping_err:
            logger.warning(f"Connection ping failed ({ping_err}). Re-establishing connection...")
            try:
                conn.close()
            except Exception:
                pass
            try:
                conn = mysql.connector.connect(**get_connection_params(role))
            except Exception as reconn_err:
                raise DatabaseUnreachableError(
                    f"Failed to reconnect to database at {Config.DB_HOST}: {reconn_err}"
                ) from reconn_err

    return conn

def get_db(role: str = None):
    """
    Flask context helper to obtain a database connection cached for the current request context.
    """
    if not hasattr(g, '_db_conns'):
        g._db_conns = {}

    target_role = role or (g.user['role'] if hasattr(g, 'user') and g.user else session.get('role', 'manager'))
    
    if target_role not in g._db_conns or not g._db_conns[target_role].is_connected():
        g._db_conns[target_role] = get_db_connection(target_role)

    return g._db_conns[target_role]

def close_db(e=None):
    """
    Closes all open connections for the request context and returns them to the pool.
    """
    db_conns = getattr(g, '_db_conns', None)
    if db_conns is not None:
        for role, conn in db_conns.items():
            if conn and conn.is_connected():
                try:
                    conn.close()
                except Exception as err:
                    logger.error(f"Error returning connection to pool: {err}")

@contextmanager
def get_db_cursor(role: str = None, dictionary: bool = True, commit: bool = False):
    """
    Safe context manager for database operations:
    Yields (conn, cursor).
    Automatically rolls back on exception, commits if commit=True and no exception,
    and safely closes cursor and connection.
    """
    conn = get_db_connection(role)
    cursor = conn.cursor(dictionary=dictionary)
    try:
        yield conn, cursor
        if commit:
            conn.commit()
    except Exception as err:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error(f"Database error during transaction (role={role}): {err}")
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
