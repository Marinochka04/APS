import tkinter as tk
from tkinter import messagebox
from threading import Thread
from time import sleep
import random
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import time

class ActionLogger:
    log = []

    @classmethod
    def add_entry(cls, source, action, details):
        queue_state = ", ".join(
            [f"{app.student.name}({app.course.title})" for app in ApplicationQueue.applications]
        ) or "Очередь пуста"
        entry = {
            "source": source,
            "action": action,
            "details": details,
            "queue_state": queue_state,
        }
        cls.log.append(entry)
        if len(cls.log) > 100:
            cls.log.pop(0)

    @classmethod
    def get_log(cls):
        formatted_log = (
            "Source            | Action                         | Details                                            | Queue State\n"
        )
        formatted_log += "-" * 130 + "\n"

        for entry in cls.log:
            formatted_log += f"{entry['source']:<17} | {entry['action']:<30} | {entry['details']:<50} | {entry['queue_state']:<40}\n"

        return formatted_log

class Student:
    def __init__(self, name, student_id):
        self.name = name
        self.id = student_id

    def apply(self, course):
        application = Application(self, course)
        return application

class Application:
    def __init__(self, student, course):
        self.student = student
        self.course = course
        self.status = "waiting"

    def submit(self):
        ActionLogger.add_entry(
            source="Student",
            action="Заявка отправлена",
            details=f"Заявка {self.student.id} отправлена на курс {self.course.title}"
        )
        self.course.receive_application(self)

    def cancel(self):
        self.status = "cancelled"

class Course:
    def __init__(self, title, capacity, school=None):
        self.title = title
        self.capacity = capacity
        self.enrolled_students = []
        self.teacher = None
        self.school = school

    def check_availability(self):
        return len(self.enrolled_students) < self.capacity

    def enroll(self, student):
        if self.check_availability():
            self.enrolled_students.append(student)
            ActionLogger.add_entry(
                source="Course",
                action="Студент записан",
                details=f"Студент {student.name} на курс {self.title}"
            )
            return True
        return False

    def assign_teacher(self, teacher):
        self.teacher = teacher
        ActionLogger.add_entry(
            source="Course",
            action="Назначен преподаватель",
            details=f"Преподаватель {teacher.name} назначен на курс {self.title}"
        )

    def receive_application(self, application):
        if self.check_availability():
            if self.enroll(application.student):
                application.status = "accepted"
                if not self.teacher and self.school:
                    self.school.assign_next_teacher(self)
        else:
            ApplicationQueue.add(application)

    def remove_random_student(self):
        if self.enrolled_students:
            student = random.choice(self.enrolled_students)
            self.enrolled_students.remove(student)
            ActionLogger.add_entry(
                source="Course",
                action="Студент удален",
                details=f"Студент {student.name} был удален с курса {self.title}"
            )

    def remove_teacher(self, school):
        if self.teacher:
            removed_teacher = self.teacher
            self.teacher = None
            ActionLogger.add_entry(
                source="Course",
                action="Преподаватель удалён",
                details=f"Преподаватель {removed_teacher.name} был удалён с курса {self.title}"
            )
            school.assign_next_teacher(self)

class ApplicationQueue:
    applications = []
    MAX_QUEUE_SIZE = 5

    @classmethod
    def add(cls, application):
        cls.applications.append(application)
        ActionLogger.add_entry(
            source="ApplicationQueue",
            action="Заявка добавлена",
            details=f"Заявка {application.student.id} добавлена в очередь"
        )

        if len(cls.applications) > cls.MAX_QUEUE_SIZE:
            cls.remove_lowest_priority()

    @classmethod
    def remove_lowest_priority(cls):
        if cls.applications:
            max_id_application = max(
                cls.applications,
                key=lambda app: app.student.id
            )
            cls.applications.remove(max_id_application)
            ActionLogger.add_entry(
                source="ApplicationQueue",
                action="Заявка удалена",
                details=f"Заявка {max_id_application.student.id} удалена из-за переполнения"
            )

    @classmethod
    def notify_school(cls):
        if cls.applications:
            School.select_application()

    @classmethod
    def process_queue(cls):
        for application in cls.applications:
            if application.course.check_availability():
                application.course.receive_application(application)
                ActionLogger.add_entry(
                    source="ApplicationQueue",
                    action="Заявка обработана",
                    details=f"Заявка {application.student.id} из очереди записана на курс {application.course.title}"
                )
                cls.applications.remove(application)

class School:
    def __init__(self, name):
        self.name = name
        self.courses = []
        self.students = []
        self.teachers = []
        self.teacher_index = 0

    def add_teacher(self, teacher):
        self.teachers.append(teacher)

    def assign_next_teacher(self, course):
        if self.teachers:
            teacher = self.teachers[self.teacher_index]
            course.assign_teacher(teacher)
            self.teacher_index = (self.teacher_index + 1) % len(self.teachers)
            ActionLogger.add_entry(
                source="School",
                action="Преподаватель назначен",
                details=f"Преподаватель {teacher.name} назначен на курс {course.title}"
            )
        else:
            ActionLogger.add_entry(
                source="School",
                action="Ошибка назначения",
                details="Нет доступных преподавателей для назначения"
            )

    @staticmethod
    def select_application():
        if ApplicationQueue.applications:
            application = ApplicationQueue.applications.pop(0)
            application.course.receive_application(application)
            ActionLogger.add_entry(
                source="School",
                action="Заявка выбрана",
                details=f"Заявка {application.student.id} выбрана для обработки"
            )

class Teacher:
    def __init__(self, name, subject):
        self.name = name
        self.subject = subject

    def teach(self, course):
        print(f"{self.name} is teaching {course.title}")

class ArtSchoolApp:
    paused = False

    def __init__(self, root, school):
        self.root = root
        self.school = school

        self.root.title("Art School Enrollment System")
        self.root.geometry("600x400")

        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)

        tk.Button(button_frame, text="Check Queue", command=self.check_queue).grid(row=0, column=0, pady=10)
        tk.Button(button_frame, text="Show Enrolled Students", command=self.show_students).grid(row=1, column=0, pady=10)
        tk.Button(button_frame, text="View Log", command=self.view_log).grid(row=2, column=0, pady=10)
        tk.Button(button_frame, text="Show Chart", command=self.show_dynamic_chart).grid(row=4, column=0, pady=10)
        tk.Button(button_frame, text="Pause/Resume", command=self.toggle_pause).grid(row=3, column=0, pady=10)

    def toggle_pause(self):
        self.paused = not self.paused
        status = "paused" if self.paused else "running"
        ActionLogger.add_entry(
            source="App",
            action="Pause/Resume",
            details=f"Application is now {status}"
        )
        messagebox.showinfo("Pause/Resume", f"Application is now {status}.")

    def check_queue(self):
        queue_status = "\n".join(
            f"{app.student.name} на курс {app.course.title}" for app in ApplicationQueue.applications
        ) or "Очередь пуста"
        messagebox.showinfo("Queue Status", queue_status)

    def show_students(self):
        course_status = "\n".join(
            f"{course.title}: {len(course.enrolled_students)}/{course.capacity} студентов"
            for course in self.school.courses
        )
        messagebox.showinfo("Course Status", course_status)

    def view_log(self):
        log_window = tk.Toplevel(self.root)
        log_window.title("Action Log")
        log_window.geometry("1200x600")

        text_box = tk.Text(log_window, wrap=tk.WORD, width=100, height=30)
        text_box.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
        text_box.config(state=tk.DISABLED)

        scrollbar = tk.Scrollbar(log_window, command=text_box.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_box.config(yscrollcommand=scrollbar.set)

        def update_log():
            if self.paused:
                log_window.after(1000, update_log)
                return

            log = ActionLogger.get_log()

            text_box.config(state=tk.NORMAL)
            text_box.delete(1.0, tk.END)
            text_box.insert(tk.END, log)
            text_box.config(state=tk.DISABLED)

            text_box.see(tk.END)

            log_window.after(1000, update_log)

        update_log()

    def show_dynamic_chart(self):
        self.chart_window = tk.Toplevel(self.root)
        self.chart_window.title("Динамическая диаграмма")

        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_window)
        self.canvas.get_tk_widget().pack()

        self.update_dynamic_chart()

    def update_dynamic_chart(self):
        course_titles = [course.title for course in self.school.courses]
        student_counts = [len(course.enrolled_students) for course in self.school.courses]

        self.ax.clear()

        self.ax.bar(course_titles, student_counts, color='purple')
        self.ax.set_title("Количество студентов на курсах")
        self.ax.set_xlabel("Курсы")
        self.ax.set_ylabel("Количество студентов")

        self.canvas.draw()

        self.chart_window.after(1000, self.update_dynamic_chart)

def generate_applications(school, app_instance):
    student_id = 1
    while True:
        if not app_instance.paused:
            name = f"Student_{student_id}"
            student = Student(name, student_id)
            school.students.append(student)

            course = random.choice(school.courses)
            application = student.apply(course)
            application.submit()

            student_id += 1
        sleep(random.randint(2, 5))

def manage_courses_and_teachers(school, app_instance):
    start_time = time.time()
    last_teacher_removal_time = 0
    delay_before_removal = 15
    lambda_removal = 1 / 30

    while True:
        if not app_instance.paused:
            for course in school.courses:
                if not course.teacher:
                    school.assign_next_teacher(course)

            current_time = time.time()

            if current_time - start_time >= delay_before_removal:
                removal_interval = random.expovariate(lambda_removal)

                if current_time - last_teacher_removal_time >= removal_interval:
                    courses_with_teachers = [course for course in school.courses if course.teacher]
                    if courses_with_teachers:
                        random.choice(courses_with_teachers).remove_teacher(school)
                        last_teacher_removal_time = current_time

            course_to_remove_from = random.choice(school.courses)
            course_to_remove_from.remove_random_student()

            ApplicationQueue.process_queue()

        sleep(5)


def main():
    course1 = Course("Painting", capacity=2)
    course2 = Course("Design", capacity=3)
    course3 = Course("Graphics", capacity=3)
    course4 = Course("Art", capacity=2)

    teacher1 = Teacher("Alice", "Painting")
    teacher2 = Teacher("Bob", "Design")

    school = School("Art School")
    school.courses = [course1, course2, course3, course4]
    school.add_teacher(teacher1)
    school.add_teacher(teacher2)

    root = tk.Tk()
    app = ArtSchoolApp(root, school)

    Thread(target=manage_courses_and_teachers, args=(school, app), daemon=True).start()
    Thread(target=generate_applications, args=(school, app), daemon=True).start()

    root.mainloop()

if __name__ == "__main__":
    main()