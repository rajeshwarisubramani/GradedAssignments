from adapters.flask_app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)

#cd "D:\code\python\GradedAssignments\LibraryManagement" python -m adapters.flask_app
#Set-Location "D:\code\python\GradedAssignments\LibraryManagement"; python -m adapters.flask_app
