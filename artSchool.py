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
        self.applications_sent = 0
        self.refusals = 0

    def apply(self, course):
        self.applications_sent += 1
        application = Application(self, course)
        return application

    def get_refusal_probability(self):
        return (self.refusals / self.applications_sent * 100) if self.applications_sent > 0 else 0.0

class Application:
    application_counter = 1

    def __init__(self, student, course):
        self.student = student
        self.course = course
        self.status = "waiting"
        self.id = Application.application_counter
        self.created_time = time.time()
        self.waiting_start_time = None
        self.waiting_completed_time = None
        self.service_start_time = None
        self.service_completed_time = None
        Application.application_counter += 1

    def submit(self):
        ActionLogger.add_entry(
            source="Student",
            action="Заявка отправлена",
            details=f"Заявка {self.id}({self.student.name}) отправлена на курс {self.course.title}"
        )
        ApplicationQueue.total_applications += 1
        self.course.receive_application(self)

    def start_waiting_process(self):
        self.waiting_start_time = time.time()
        # ActionLogger.add_entry(
        #     source="Application",
        #     action="Начало ожидания заявки",
        #     details=f"Заявка {self.id} ({self.student.name}) начала ожидание на курс {self.course.title} в {self.waiting_start_time:.2f} секунд"
        # )

    def complete_waiting_process(self):
        self.waiting_completed_time = time.time()
        # ActionLogger.add_entry(
        #     source="Application",
        #     action="Завершение ожидания заявки",
        #     details=f"Заявка {self.id} ({self.student.name}) завершено ожидание на курс {self.course.title} в {self.waiting_completed_time:.2f} секунд"
        # )

    def start_service_process(self):
        self.service_start_time = time.time()
        # ActionLogger.add_entry(
        #     source="Application",
        #     action="Начало обслуживания заявки",
        #     details=f"Заявка {self.id} ({self.student.name}) начато обслуживание заявки на курсе {self.course.title} в {self.service_start_time:.2f} секунд"
        # )

    def complete_service_process(self):
        if self.service_start_time is None:
            raise ValueError(f"Время начала обслуживания заявки для {self.id} не установлено.")

        self.service_completed_time = time.time()
        service_time = self.service_completed_time - self.service_start_time
        details = f"Заявка {self.id} ({self.student.name}) завершено обслуживание заявки на курсе {self.course.title} в {service_time:.2f} секунд"

        # ActionLogger.add_entry(
        #     source="Application",
        #     action="Завершение обслуживания заявки",
        #     details=details
        # )

    def cancel(self):
        self.status = "cancelled"

class Course:
    def __init__(self, title, capacity, school=None):
        self.title = title
        self.capacity = capacity
        self.enrolled_students = []
        self.teacher = None
        self.teacher_assigned_time = None
        self.teacher_start_time = None
        self.teacher_end_time = None
        self.school = school

    def check_availability(self):
        return len(self.enrolled_students) < self.capacity

    def enroll(self, student, application=None):
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
        self.teacher_assigned_time = time.time()
        self.teacher_start_time = time.time()
        teacher.start_work_on_course()
        ActionLogger.add_entry(
            source="Course",
            action="Назначен преподаватель",
            details=f"Преподаватель {teacher.name} назначен на курс {self.title}"
        )

    def receive_application(self, application):
        if self.check_availability():
            if self.enroll(application.student):
                application.status = "accepted"
                ApplicationQueue.processed_applications.append(application)
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

            related_application = next(
                (
                    app
                    for app in ApplicationQueue.applications + ApplicationQueue.processed_applications
                    if app.student == student and app.course.title == self.title
                ),
                None
            )
            if related_application:
                related_application.complete_service_process()
                print(f"Лог заявки: {ActionLogger.log[-1]}")
            else:
                print(f"Связанная заявка для студента {student.name} не найдена.")

    def remove_teacher(self, school):
        if self.teacher:
            removed_teacher = self.teacher
            self.teacher_end_time = time.time()  # Завершаем отслеживание времени работы на курсе
            self.teacher.end_work_on_course()  # Завершаем работу преподавателя на курсе
            self.teacher = None #############################
            ActionLogger.add_entry(
                source="Course",
                action="Преподаватель удалён",
                details=f"Преподаватель {removed_teacher.name} был удалён с курса {self.title}"
            )
            school.assign_next_teacher(self)
class ApplicationQueue:
    applications = []
    processed_applications = []
    MAX_QUEUE_SIZE = 3

    total_applications = 0
    total_refusals = 0

    statistics_time = None

    @classmethod
    def add(cls, application):
        cls.applications.append(application)

        ActionLogger.add_entry(
            source="ApplicationQueue",
            action="Заявка добавлена",
            details=f"Заявка {application.id}({application.student.name}) добавлена в очередь"
        )

        if len(cls.applications) > cls.MAX_QUEUE_SIZE:
            cls.remove_lowest_priority()

    @classmethod
    def remove_lowest_priority(cls):
        if cls.applications:
            application_to_remove = max(cls.applications, key=lambda app: app.student.id)
            application_to_remove.student.refusals += 1

            application_to_remove.complete_waiting_process()

            cls.applications.remove(application_to_remove)
            cls.total_refusals += 1

            ActionLogger.add_entry(
                source="ApplicationQueue",
                action="Заявка удалена",
                details=f"Заявка {application_to_remove.id}({application_to_remove.student.name}) удалена из-за переполнения"
            )

    @classmethod
    def get_refusals(cls):
        refusal_rate = (cls.total_refusals / cls.total_applications * 100) if cls.total_applications > 0 else 0
        return cls.total_applications, cls.total_refusals, refusal_rate

    @classmethod
    def notify_school(cls):
        if cls.applications:
            School.select_application()

    @classmethod
    def process_queue(cls):
        cls.applications.sort(key=lambda app: app.id)

        for application in cls.applications:
            if application.course.check_availability():
                application.course.receive_application(application)
                application.complete_waiting_process()
                ActionLogger.add_entry(
                    source="ApplicationQueue",
                    action="Заявка обработана",
                    details=f"Заявка {application.id}({application.student.name}) из очереди записана на курс {application.course.title}"
                )

                cls.applications.remove(application)

    @classmethod
    def finalize_statistics(cls):
        cls.statistics_time = time.time()

    @staticmethod
    def calculate_statistics():
        total_waiting_time = 0
        total_service_time = 0
        processed_applications = 0

        waiting_times = []
        service_times = []

        current_time = ApplicationQueue.statistics_time or time.time()

        all_applications = ApplicationQueue.processed_applications + ApplicationQueue.applications

        print("\n=== Начало расчета статистики ===")
        print(f"Текущее время: {current_time}")
        print(f"Всего заявок для обработки: {len(ApplicationQueue.processed_applications)} + {len(ApplicationQueue.applications)}")

        for idx, application in enumerate(all_applications):
            print(f"\n--- Обработка заявки {idx + 1} ---")
            print(f"ID заявки: {application.id}, Студент: {application.student.name}, Курс: {application.course.title}")

            if application.waiting_completed_time and application.waiting_start_time:
                waiting_time = application.waiting_completed_time - application.waiting_start_time
                print(
                    f"Время ожидания завершено: {application.waiting_completed_time}, Начало: {application.waiting_start_time}, Итог: {waiting_time}")
            else:
                waiting_time = 0
                print("Время ожидания не завершено, установлено в 0")

            if application.service_start_time and application.service_completed_time:
                service_time = application.service_completed_time - application.service_start_time
                print(
                    f"Время обслуживания завершено: {application.service_completed_time}, Начало: {application.service_start_time}, Итог: {service_time}")
            else:
                service_time = 20
                print("Время обслуживания не завершено, установлено в 20")

            total_waiting_time += waiting_time
            total_service_time += service_time
            waiting_times.append(waiting_time)
            service_times.append(service_time)
            processed_applications += 1

        print("\n=== Итоги обработки всех заявок ===")
        print(f"Общее время ожидания: {total_waiting_time}")
        print(f"Общее время обслуживания: {total_service_time}")
        print(f"Обработано заявок: {processed_applications}")

        if processed_applications > 0:
            average_waiting_time = total_waiting_time / processed_applications
            average_processing_time = total_service_time / processed_applications
            variance_waiting_time = sum(
                (wt - average_waiting_time) ** 2 for wt in waiting_times) / processed_applications
            variance_processing_time = sum(
                (st - average_processing_time) ** 2 for st in service_times) / processed_applications
            print(f"Среднее время ожидания: {average_waiting_time}")
            print(f"Среднее время обслуживания: {average_processing_time}")
            print(f"Дисперсия время ожидания: {variance_waiting_time}")
            print(f"Дисперсия время обслуживания: {variance_processing_time}")
        else:
            average_waiting_time = average_processing_time = variance_waiting_time = variance_processing_time = 0
            print("Заявок для обработки не найдено.")

        print("=== Конец расчета статистики ===\n")

        return average_waiting_time, average_processing_time, variance_waiting_time, variance_processing_time

class School:
    def __init__(self, name):
        self.name = name
        self.courses = []
        self.students = []
        self.teachers = []
        self.teacher_index = 0
        self.total_assignments = 0
        self.start_time = time.time()  # Время начала работы школы

    def add_teacher(self, teacher):
        teacher.assignment_count = 0
        self.teachers.append(teacher)

    def assign_next_teacher(self, course):
        if self.teachers:
            teacher = self.teachers[self.teacher_index]
            course.assign_teacher(teacher)

            teacher.assignment_count += 1
            self.total_assignments += 1

            self.teacher_index = (self.teacher_index + 1) % len(self.teachers)
            ActionLogger.add_entry(
                source="School",
                action="Преподаватель назначен",
                details=f"Преподаватель {teacher.name} назначен на курс {course.title}"
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

    def get_teacher_utilization(self):
        utilization_data = {}
        for teacher in self.teachers:
            is_busy = any(course.teacher == teacher for course in self.courses)
            total_courses = len(self.courses)
            busy_courses = sum(1 for course in self.courses if course.teacher == teacher)
            utilization = (busy_courses / total_courses * 100) if total_courses > 0 else 0
            utilization_data[teacher] = (is_busy, utilization)
        return utilization_data

    def get_teacher_utilization_ratios(self):
        utilization_ratios = {}
        for teacher in self.teachers:
            ratio = teacher.assignment_count / self.total_assignments if self.total_assignments > 0 else 0.0
            utilization_ratios[teacher.name] = ratio
        return utilization_ratios

    def get_system_utilization(self):
        total_courses = len(self.courses)
        busy_courses = sum(1 for course in self.courses if course.teacher is not None)
        utilization = (busy_courses / total_courses * 100) if total_courses > 0 else 0
        return utilization

    def calculate_teacher_load(self):
        teacher_load = {}
        for teacher in self.teachers:
            total_time = 0
            for course in self.courses:
                if course.teacher == teacher:
                    # Рассчитываем время работы на курсе
                    if course.teacher_start_time:
                        time_on_course = time.time() - course.teacher_start_time
                        total_time += time_on_course

            # Загрузка = время работы / общее время с момента назначения
            load = total_time / (time.time() - teacher.assignment_time) if total_time > 0 else 0
            teacher_load[teacher.name] = load * 100  # Выражаем в процентах

        return teacher_load

    def show_teacher_work_time(self):
        teacher_summary = "Преподаватель | Курс       | Время работы (сек)\n" + "-" * 50 + "\n"

        for teacher in self.teachers:
            for course in self.courses:
                work_time = teacher.get_work_time_for_course(course)
                teacher_summary += f"{teacher.name:<14} | {course.title:<10} | {work_time:.2f}\n"

        return teacher_summary

class Teacher:
    def __init__(self, name, subject, assignment_time=None):
        self.name = name
        self.subject = subject
        self.assignment_count = 0
        self.assignment_time = assignment_time or time.time()
        self.total_work_time = 0
        self.assignment_start_time = None
        self.assignment_end_time = None
        self.course_times = {}

    def start_work_on_course(self):
        self.assignment_start_time = time.time()

    def end_work_on_course(self):
        if self.assignment_start_time:
            self.assignment_end_time = time.time()
            work_duration = self.assignment_end_time - self.assignment_start_time
            self.total_work_time += work_duration
            self.assignment_start_time = None ###########################

    def get_work_time_for_course(self, course):
        return self.course_times.get(course.title, 0)

    def record_course_time(self, course, time_spent):
        if course.title not in self.course_times:
            self.course_times[course.title] = 0
        self.course_times[course.title] += time_spent

    def get_total_time_spent(self):
        return sum(self.course_times.values())

class ArtSchoolApp:
    paused = False

    def __init__(self, root, school, students_pool):
        self.root = root
        self.school = school
        self.students_pool = students_pool
        self.application_limit = tk.IntVar(value=0)

        self.root.title("Art School Enrollment System")
        self.root.geometry("600x400")

        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)

        tk.Label(button_frame, text="Number of applications:").grid(row=0, column=0, pady=10, sticky=tk.W)
        tk.Entry(button_frame, textvariable=self.application_limit).grid(row=0, column=1, pady=10)

        tk.Button(button_frame, text="Check Queue", command=self.check_queue).grid(row=1, column=0, pady=10)
        tk.Button(button_frame, text="Show Enrolled Students", command=self.show_students).grid(row=2, column=0,
                                                                                                pady=10)
        tk.Button(button_frame, text="View Log", command=self.view_log).grid(row=3, column=0, pady=10)
        tk.Button(button_frame, text="Show Chart", command=self.show_dynamic_chart).grid(row=4, column=0, pady=10)
        tk.Button(button_frame, text="Show Refusals", command=self.show_refusals).grid(row=5, column=0, pady=10)
        tk.Button(button_frame, text="Show Teacher Utilization", command=self.show_teacher_utilization).grid(row=6,
                                                                                                             column=0,
                                                                                                             pady=10)

        tk.Button(button_frame, text="Pause/Resume", command=self.toggle_pause).grid(row=7, column=0, pady=10)

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
        if hasattr(self, 'students_window') and self.students_window.winfo_exists():
            self.update_students_window()
        else:
            self.students_window = tk.Toplevel(self.root)
            self.students_window.title("Enrolled Students")
            self.students_window.geometry("600x200")

            self.students_label = tk.Label(self.students_window, text="", justify=tk.LEFT)
            self.students_label.pack(pady=10, padx=10)

            self.update_students_window()

    def update_students_window(self):
        course_status = ""
        for course in self.school.courses:
            enrolled_students = ", ".join(student.name for student in course.enrolled_students) or "Нет студентов"
            course_status += f"{course.title} ({len(course.enrolled_students)}/{course.capacity} студентов): {enrolled_students}\n"

        self.students_label.config(text=course_status)
        self.students_window.after(1000, self.update_students_window)

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

    def show_refusals(self):
        if hasattr(self, 'refusals_window') and self.refusals_window.winfo_exists():
            self.update_refusals_window()
        else:
            self.refusals_window = tk.Toplevel(self.root)
            self.refusals_window.title("Refusals")

            self.refusals_label = tk.Label(self.refusals_window, text="", justify=tk.LEFT)
            self.refusals_label.pack(pady=10, padx=10)

            self.update_refusals_window()

    def update_refusals_window(self):
        total_applications, total_refusals, refusal_rate = ApplicationQueue.get_refusals()
        stats_table = f"""
        Число заявок: {total_applications}
        Число отказов: {total_refusals}
        Процент отказов: {refusal_rate:.2f}%
        """
        self.refusals_label.config(text=stats_table)
        self.refusals_window.after(1000, self.update_refusals_window)

    def show_teacher_utilization(self):
        if hasattr(self, 'utilization_window') and self.utilization_window.winfo_exists():
            self.update_teacher_utilization_window()
        else:
            self.utilization_window = tk.Toplevel(self.root)
            self.utilization_window.title("Teacher Utilization")

            self.utilization_label = tk.Label(self.utilization_window, text="", justify=tk.LEFT)
            self.utilization_label.pack(pady=10, padx=10)

            self.update_teacher_utilization_window()

    def update_teacher_utilization_window(self):
        utilization_data = self.school.get_teacher_utilization()
        utilization_table = "Прибор         | Занятость | % Занятости\n" + "-" * 35 + "\n"
        for teacher, (is_busy, utilization) in utilization_data.items():
            status = "Занят" if is_busy else "Свободен"
            utilization_table += f"{teacher.name:<14} | {status:<9} | {utilization:.2f}%\n"

        self.utilization_label.config(text=utilization_table)
        self.utilization_window.after(1000, self.update_teacher_utilization_window)

    def show_summary_table(self):
        summary_window = tk.Toplevel(self.root)
        summary_window.title("Итоговая таблица")
        summary_window.geometry("600x400")

        total_applications, total_refusals, refusal_rate = ApplicationQueue.get_refusals()
        total_students = len(self.students_pool)

        summary_label = tk.Label(summary_window, text="Общие данные", font=("Arial", 14, "bold"))
        summary_label.pack(pady=10)
        summary_text = f"""
        Количество источников (студентов): {total_students}
        Общее количество заявок: {total_applications}
        Размер буфера: {ApplicationQueue.MAX_QUEUE_SIZE}
        Число отказов: {total_refusals}
        Вероятность отказа: {refusal_rate:.2f}%
        """
        summary_data_label = tk.Label(summary_window, text=summary_text, justify=tk.LEFT)
        summary_data_label.pack(pady=10)

        show_student_summary_button = tk.Button(
            summary_window, text="Показать таблицу заявок студентов (источников)", command=self.show_student_summary_table
        )
        show_student_summary_button.pack(pady=10)

        show_teacher_summary_button = tk.Button(
            summary_window, text="Показать таблицу занятости преподавателей (приборов)", command=self.show_teacher_summary_table
        )
        show_teacher_summary_button.pack(pady=10)

        show_time_statistics_button = tk.Button(
            summary_window, text="Показать временную статистику", command=self.show_time_statistics
        )
        show_time_statistics_button.pack(pady=10)

    def show_student_summary_table(self):
        student_summary_window = tk.Toplevel(self.root)
        student_summary_window.title("Таблица заявок студентов")
        student_summary_window.geometry("600x400")

        student_summary = "Студент           | Кол-во заявок | Кол-во отказов | Вероятность отказа (%)\n"
        student_summary += "-" * 65 + "\n"

        for student in self.students_pool:
            refusal_rate = student.get_refusal_probability()
            student_summary += f"{student.name:<17} | {student.applications_sent:^13} | {student.refusals:^14} | {refusal_rate:>8.2f}%\n"

        student_summary_label = tk.Label(
            student_summary_window, text=student_summary, justify=tk.LEFT, font=("Courier", 10)
        )
        student_summary_label.pack(pady=10)

    def show_teacher_summary_table(self):
        teacher_summary_window = tk.Toplevel(self.root)
        teacher_summary_window.title("Время работы преподавателей на курсах")
        teacher_summary_window.geometry("600x400")

        teacher_summary = self.school.show_teacher_work_time()

        teacher_summary_label = tk.Label(
            teacher_summary_window, text=teacher_summary, justify=tk.LEFT,
            font=("Courier", 10)
        )
        teacher_summary_label.pack(pady=10)

    def show_time_statistics(self):
        (
            average_waiting_time,
            average_processing_time,
            variance_waiting_time,
            variance_processing_time,
        ) = ApplicationQueue.calculate_statistics()

        average_system_time = average_waiting_time + average_processing_time

        stats_message = f"""
        Среднее время ожидания (Tож): {average_waiting_time:.2f} секунд
        Среднее время обслуживания (Tобсл): {average_processing_time:.2f} секунд
        Среднее время в системе (Твс): {average_system_time:2f} секунд
        Дисперсия времени ожидания (Dож): {variance_waiting_time:.2f}
        Дисперсия времени обслуживания (Dобсл): {variance_processing_time:.2f}
        """
        messagebox.showinfo("Временная статистика", stats_message)

def generate_applications(school, app_instance, students_pool):
    application_count = 0

    while True:
        if not app_instance.paused:
            limit = app_instance.application_limit.get()

            if limit > 0 and application_count >= limit:
                app_instance.paused = True
                ApplicationQueue.finalize_statistics()
                app_instance.show_summary_table()
                break

            student = random.choice(students_pool)
            course = random.choice(school.courses)

            already_enrolled = student in course.enrolled_students
            already_in_queue = any(app.student == student and app.course == course for app in ApplicationQueue.applications)

            if not already_enrolled and not already_in_queue:
                application = student.apply(course)
                application.submit()
                application.start_waiting_process()
                application_count += 1

                if student in course.enrolled_students:
                    application.complete_waiting_process()
                    application.start_service_process()

                    while application.service_start_time is None:
                        sleep(0.1)

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
                    course.teacher.end_work_on_course(course) #
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

        sleep(10)

def main():
    course1 = Course("Painting", capacity=2)
    course2 = Course("Design", capacity=3)
    course3 = Course("Graphics", capacity=3)
    course4 = Course("Art", capacity=2)

    teacher1 = Teacher("Alice", "Painting")
    teacher2 = Teacher("Bob", "Design")
    teacher3 = Teacher("Cony", "Art")

    school = School("Art School")
    school.courses = [course1, course2, course3, course4]
    school.add_teacher(teacher1)
    school.add_teacher(teacher2)
    school.add_teacher(teacher3)

    students_pool = [Student(f"Student_{i}", i) for i in range(1, 11)]

    root = tk.Tk()
    app = ArtSchoolApp(root, school, students_pool)

    Thread(target=manage_courses_and_teachers, args=(school, app), daemon=True).start()
    Thread(target=generate_applications, args=(school, app, students_pool), daemon=True).start()

    root.mainloop()

if __name__ == "__main__":
    main()