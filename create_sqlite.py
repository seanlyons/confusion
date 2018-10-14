import sqlite3
import sys
'''
    http://www.sqlitetutorial.net/sqlite-python/create-tables/
'''

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as e:
        print('1 ERROR: ' + str(e))
        sys.exit()
 
    return None

def execute_statement(conn, statement):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(statement)
    except Exception as e:
        print('2 ERROR: ' + str(e) + " for statement: \n\n" + statement)
        sys.exit()

def main():
    database_name = "confusion.db"
 
    #statement = file('schema.sql').read().split('\n\n')
    with open('schema.sql') as f:
        statement = f.read().split('\n\n')
 
    # create a database connection
    conn = create_connection(database_name)
    if conn is not None:
        # create projects table
        for s in statement:
            execute_statement(conn, s)
    else:
        print("Error! cannot create the database connection.")

if __name__ == '__main__':
    main()
