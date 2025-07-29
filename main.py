from http.server import SimpleHTTPRequestHandler, HTTPServer
import os
import json
import uuid
import urllib.parse

# Define constants and session management
ADMIN_PASSWORD = "admin123"  # Change this to your actual admin password
TEMPLATES_DIR = './templates'
DATA_DIR = './data'
SESSION_FILE = os.path.join(DATA_DIR, 'session.json')

# Utility functions to load and save JSON data
def load_json(file):
    with open(file, "r") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# Template rendering function with context replacement
def render_template(template_name, context=None):
    context = context or {}
    # Inject is_logged_in for all templates
    context["is_logged_in"] = ExamHandler.is_admin_authenticated_static()
    path = os.path.join(TEMPLATES_DIR, template_name)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple processing for if/else conditionals
    if "{% if " in content:
        for key, val in context.items():
            if key == "found":
                if val:
                    parts = content.split("{% if found %}")
                    if len(parts) > 1:
                        else_parts = parts[1].split("{% else %}")
                        if len(else_parts) > 1:
                            content = parts[0] + else_parts[0] + else_parts[1].split("{% endif %}")[1]
                else:
                    parts = content.split("{% if found %}")
                    if len(parts) > 1:
                        else_parts = parts[1].split("{% else %}")
                        if len(else_parts) > 1:
                            content = parts[0] + else_parts[1].split("{% endif %}")[1]

    # Regular variable substitution
    for key, val in context.items():
        content = content.replace(f'{{{{ {key} }}}}', str(val))

    return content

# HTTP request handler
class ExamHandler(SimpleHTTPRequestHandler):
    def is_admin_authenticated(self):
        return self.is_admin_authenticated_static()

    @staticmethod
    def is_admin_authenticated_static():
        if os.path.exists(SESSION_FILE):
            session = load_json(SESSION_FILE)
            return session.get("admin_logged_in", False)
        return False

    def do_GET(self):
        if self.path == '/':
            self.path = '/templates/index.html'

        elif self.path == '/admin':
            if not self.is_admin_authenticated():
                html = render_template('admin_login.html', {'error': ''})
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())
                return
            else:
                self.send_response(303)
                self.send_header('Location', '/templates/dashboard.html')
                self.end_headers()
                return

        elif self.path == '/templates/dashboard.html':
            if not self.is_admin_authenticated():
                self.send_response(303)
                self.send_header('Location', '/admin')
                self.end_headers()
                return

            students = load_json('data/students.json')
            invigilators = load_json('data/invigilators.json')
            halls = load_json('data/halls.json')

            student_list = ''.join(f"<li>{s['name']} ({s['roll']})</li>" for s in students)
            invigilator_list = ''.join(f"<li>{i['name']} ({i['email']})</li>" for i in invigilators)
            hall_list = ''.join(f"<li>{h['name']} ({h['rows']}x{h['cols']})</li>" for h in halls)

            content = render_template("dashboard.html", {
                "student_list": student_list,
                "invigilator_list": invigilator_list,
                "hall_list": hall_list
            })

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content.encode())
            return

        elif self.path == '/logout':
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            self.send_response(303)
            self.send_header('Location', '/admin')
            self.end_headers()
            return

        elif self.path in ['/templates/student.html', '/templates/invigilator.html']:
            template_name = os.path.basename(self.path)
            html = render_template(template_name, {'result': ''})
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
            return

        return super().do_GET()

    def do_POST(self):
        length = int(self.headers['Content-Length'])
        post_data = urllib.parse.parse_qs(self.rfile.read(length).decode())

        if self.path == '/admin_login':
            password = post_data.get('password', [''])[0]
            if password == ADMIN_PASSWORD:
                save_json(SESSION_FILE, {"admin_logged_in": True})
                self.send_response(303)
                self.send_header('Location', '/templates/dashboard.html')
                self.end_headers()
            else:
                html = render_template('admin_login.html', {'error': 'Incorrect password'})
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())
            return

        if not self.is_admin_authenticated():
            self.send_response(303)
            self.send_header('Location', '/admin')
            self.end_headers()
            return

        if self.path == '/add_student':
            name = post_data.get('name', [''])[0]
            roll = post_data.get('roll', [''])[0]
            students = load_json('data/students.json')
            if not any(s['roll'] == roll for s in students):
                students.append({'name': name, 'roll': roll})
                save_json('data/students.json', students)

        elif self.path == '/add_invigilator':
            name = post_data.get('name', [''])[0]
            email = post_data.get('email', [''])[0].strip().lower()
            invigs = load_json('data/invigilators.json')
            if not any(i['email'] == email for i in invigs):
                invigs.append({'name': name, 'email': email})
                save_json('data/invigilators.json', invigs)

        elif self.path == '/add_hall':
            name = post_data.get('name', [''])[0]
            rows = int(post_data.get('rows', [0])[0])
            cols = int(post_data.get('columns', [0])[0])
            halls = load_json('data/halls.json')
            if rows > 0 and cols > 0:
                existing = next((h for h in halls if h['name'] == name), None)
                if existing:
                    existing['rows'] = rows
                    existing['cols'] = cols
                else:
                    halls.append({'name': name, 'rows': rows, 'cols': cols})
                save_json('data/halls.json', halls)

        elif self.path == '/generate':
            try:
                from generate_allocation import generate
                students = load_json('data/students.json')
                halls = load_json('data/halls.json')
                invigilators = load_json('data/invigilators.json')
                total_seats = sum(h['rows'] * h['cols'] for h in halls)
        
                if total_seats < len(students):
                    error_message = "❌ Not enough seats."
                elif len(invigilators) < len(halls):
                    error_message = "❌ Not enough invigilators."
                else:
                    generate()
                    error_message = None  # Success case, no error
        
        # Send the response back to the client with the error message
                if error_message:
                    html = render_template('dashboard.html', {
                        'error_message': error_message  # Passing the error message to the template
                    })
                else:
                    html = render_template('dashboard.html', {
                        'success_message': "✅ Allocation generated successfully!"  # Success message
                    })
        
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())
        
            except Exception as e:
                error_message = f"❌ Error during generation: {e}"
                html = render_template('dashboard.html', {'error_message': error_message})
                self.send_response(500)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(html.encode())

        elif self.path == '/reset_all':
            for file in ['students.json', 'invigilators.json', 'halls.json', 'allocations.json', 'duties.json']:
                save_json(f'data/{file}', [])

        elif self.path == '/student_lookup':
            roll = post_data.get('roll', [''])[0]
            allocs = load_json('data/allocations.json')
            allocation = next((a for a in allocs if a['roll'] == roll), None)
            if allocation:
                hall_name = allocation['hall'].strip()
                seat_position = f"Row {allocation['row']}, Col {allocation['column']}"
                html = render_template('student.html', {
                    'result': f"Seated at {hall_name} (Row {allocation['row']}, Col {allocation['column']})",
                    'hall_name': hall_name,
                    'seat_position': seat_position,
                    'found': True
                })
            else:
                html = render_template('student.html', {
                    'result': "Not found",
                    'hall_name': '',
                    'seat_position': '',
                    'found': False
                })
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
            return

        elif self.path == '/invigilator_lookup':
            email = post_data.get('email', [''])[0]
            duties = load_json('data/duties.json')
            duty = next((d for d in duties if d['email'] == email), None)
            if duty:
                hall_name = duty['hall'].strip()
                html = render_template('invigilator.html', {
                    'result': f"You are assigned to {hall_name}",
                    'duty_hall': hall_name,
                    'has_duty': True
                })
            else:
                html = render_template('invigilator.html', {
                    'result': "No duty assigned",
                    'duty_hall': '',
                    'has_duty': False
                })
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode())
            return

        self.send_response(303)
        self.send_header('Location', '/templates/dashboard.html')
        self.end_headers()

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    for file in ['students.json', 'invigilators.json', 'halls.json', 'allocations.json', 'duties.json']:
        path = os.path.join(DATA_DIR, file)
        if not os.path.exists(path):
            save_json(path, [])
    server = HTTPServer(('localhost', 8083), ExamHandler)
    print("Server running on http://localhost:8083")
    server.serve_forever()
