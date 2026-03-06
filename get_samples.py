from app.core.database import execute_query

def get_sample_data():
    data = {}
    
    student = execute_query("SELECT student_id FROM students LIMIT 1", fetch_one=True)
    if student: data['student_id'] = student['student_id']
    
    parent = execute_query("SELECT parent_id FROM parents LIMIT 1", fetch_one=True)
    if parent: data['parent_id'] = parent['parent_id']
    
    route = execute_query("SELECT route_id FROM routes LIMIT 1", fetch_one=True)
    if route: data['route_id'] = route['route_id']
    
    cls = execute_query("SELECT class_id FROM classes LIMIT 1", fetch_one=True)
    if cls: data['class_id'] = cls['class_id']
    
    trip = execute_query("SELECT trip_id FROM trips LIMIT 1", fetch_one=True)
    if trip: data['trip_id'] = trip['trip_id']
    
    import json
    print(json.dumps(data, indent=2))

if __name__ == "__main__":
    get_sample_data()
