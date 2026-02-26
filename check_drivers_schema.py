from app.core.database import execute_query

def check_schema():
    try:
        # Check column names in 'drivers' table
        result = execute_query("DESCRIBE drivers", fetch_all=True)
        if result:
            print("Columns in 'drivers' table:")
            for row in result:
                print(f"- {row['Field']} ({row['Type']})")
        else:
            print("Table 'drivers' not found or empty.")
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()
