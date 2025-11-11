from django.core.management.base import BaseCommand
from django.db import transaction
from academics.models import Quiz, Question, QuestionOption, Module, Course

import csv


class Command(BaseCommand):
    help = 'Import quiz questions and options from a CSV file into Quizzes of Modules'

    def add_arguments(self, parser):
        parser.add_argument('course_id', type=int, help='course id')
        parser.add_argument('module_id', type=int, help='module id')
        parser.add_argument('csv_file', type=str, help='Path to the CSV file containing the quiz data')

    @transaction.atomic
    def handle(self, *args, **options):
        course_id = options['course_id']
        module_id = options['module_id']
        file_path = options['csv_file']

        # Fetch the specific Module and Quiz
        course = Course.objects.get(pk=course_id)
        module = Module.objects.get(pk=module_id, course=course)

        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                quiz, _ = Quiz.objects.get_or_create(title=row['Quiz'], order=1, module=module)
                question_text = row['Question']
                correct_answer = row['Correct']

                # Create the question
                question, _ = Question.objects.get_or_create(
                    quiz=quiz,
                    text=question_text,
                    defaults={'question_type': 'MCQ'}  # Assuming all questions are MCQ
                )

                # Create options
                for option in ['A', 'B', 'C', 'D']:
                    QuestionOption.objects.get_or_create(
                        question=question,
                        text=row[option],
                        defaults={'is_correct': (correct_answer == option)}
                    )

                self.stdout.write(self.style.SUCCESS(f'Successfully imported question: "{question_text}"'))
