import json
import os

DATA_DIR = 'data'

def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'r') as f:
        return json.load(f)

def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def generate():
    students = load_json('students.json')
    invigilators = load_json('invigilators.json')
    halls = load_json('halls.json')

    allocations = []
    duties = []

    student_index = 0
    total_students = len(students)

    # Seat students
    for hall in halls:
        hall_name = hall['name']
        rows = hall['rows']
        cols = hall['cols']

        for r in range(1, rows + 1):
            for c in range(1, cols + 1):
                if student_index < total_students:
                    student = students[student_index]
                    allocations.append({
                        'roll': student['roll'],
                        'name': student['name'],
                        'hall': hall_name,
                        'row': r,
                        'column': c
                    })
                    student_index += 1

    # Assign invigilators
    for i, hall in enumerate(halls):
        if i < len(invigilators):
            inv = invigilators[i]
            duties.append({
                'hall': hall['name'],
                'name': inv['name'],
                'email': inv['email'].strip().lower()
            })

    save_json('allocations.json', allocations)
    save_json('duties.json', duties)

if __name__ == '__main__':
    generate()
    print("✅ Allocations and duties generated.")
