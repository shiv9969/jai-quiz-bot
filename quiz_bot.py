import os
import json
import random
import telebot
from telebot import types
from datetime import datetime

# Initialize bot with your token
BOT_TOKEN = ""
bot = telebot.TeleBot(BOT_TOKEN)

# Store user states
user_states = {}
user_scores = {}
last_messages = {}  # Store last message IDs for deletion

class UserState:
    def __init__(self):
        self.semester = None
        self.subject = None
        self.unit = None
        self.current_question = 0
        self.questions = []
        self.score = 0
        self.start_time = None

# Load available semesters and subjects
def load_subjects():
    subjects = {}
    for semester in os.listdir():
        if semester.startswith("semester"):
            subjects[semester] = []
            for subject in os.listdir(semester):
                if subject.endswith(".json"):
                    subjects[semester].append(subject[:-5])  # Remove .json extension
    return subjects

AVAILABLE_SUBJECTS = load_subjects()

def delete_previous_message(chat_id):
    if chat_id in last_messages:
        try:
            bot.delete_message(chat_id, last_messages[chat_id])
        except:
            pass  # Message might be already deleted or too old

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
                 "Welcome to the Pharmacy Quiz Bot! 📚\n\n"
                 "Available commands:\n"
                 "/quiz - Start a new quiz\n"
                 "/stats - View your quiz statistics\n"
                 "/help - Show this help message\n"
                 "/about - About this bot")

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message,
                 "How to use this bot:\n\n"
                 "1. Send /quiz to start a new quiz\n"
                 "2. Select the semester\n"
                 "3. Select the subject\n"
                 "4. Select the unit\n"
                 "5. Answer 10 random questions\n"
                 "6. Get your score!\n\n"
                 "Other commands:\n"
                 "/stats - View your quiz statistics\n"
                 "/cancel - Cancel current quiz\n"
                 "/about - About this bot")

@bot.message_handler(commands=['about'])
def send_about(message):
    bot.reply_to(message,
                 "🤖 Pharmacy Quiz Bot\n\n"
                 "This bot helps pharmacy students practice with MCQs from various subjects.\n\n"
                 "Features:\n"
                 "- Multiple subjects and units\n"
                 "- Random questions each time\n"
                 "- Score tracking\n"
                 "- Performance statistics\n\n"
                 "Created with ❤️ for pharmacy students")

@bot.message_handler(commands=['cancel'])
def cancel_quiz(message):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
        bot.reply_to(message, "Quiz cancelled. Send /quiz to start a new one!")
    else:
        bot.reply_to(message, "No active quiz to cancel.")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    user_id = message.from_user.id
    if user_id in user_scores:
        stats = user_scores[user_id]
        total_quizzes = stats.get('total_quizzes', 0)
        avg_score = stats.get('total_score', 0) / total_quizzes if total_quizzes > 0 else 0
        high_score = stats.get('highest_score', 0)
        
        stats_message = (
            "📊 Your Quiz Statistics:\n\n"
            f"Total Quizzes: {total_quizzes}\n"
            f"Average Score: {avg_score:.1f}/10\n"
            f"Highest Score: {high_score}/10\n"
        )
        bot.reply_to(message, stats_message)
    else:
        bot.reply_to(message, "You haven't taken any quizzes yet. Send /quiz to start!")

@bot.message_handler(commands=['quiz'])
def start_quiz(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    user_states[user_id] = UserState()
    
    # Create inline keyboard with semester options
    markup = types.InlineKeyboardMarkup(row_width=2)
    semester_buttons = [
        types.InlineKeyboardButton(sem, callback_data=f"sem_{sem}") 
        for sem in AVAILABLE_SUBJECTS.keys()
    ]
    markup.add(*semester_buttons)
    
    # Delete previous message if exists
    delete_previous_message(chat_id)
    
    # Send new message and store its ID
    sent_msg = bot.send_message(chat_id, "Please select a semester:", reply_markup=markup)
    last_messages[chat_id] = sent_msg.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith('sem_'))
def handle_semester_selection(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    semester = call.data[4:]  # Remove 'sem_' prefix
    
    if semester not in AVAILABLE_SUBJECTS:
        bot.answer_callback_query(call.id, "Invalid semester. Please try again.")
        return
    
    user_states[user_id].semester = semester
    
    # Create inline keyboard with subject options
    markup = types.InlineKeyboardMarkup(row_width=2)
    subject_buttons = [
        types.InlineKeyboardButton(subj, callback_data=f"subj_{subj}") 
        for subj in AVAILABLE_SUBJECTS[semester]
    ]
    markup.add(*subject_buttons)
    
    # Delete previous message
    delete_previous_message(chat_id)
    
    # Send new message and store its ID
    sent_msg = bot.send_message(chat_id, "Please select a subject:", reply_markup=markup)
    last_messages[chat_id] = sent_msg.message_id
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('subj_'))
def handle_subject_selection(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    subject = call.data[5:]  # Remove 'subj_' prefix
    semester = user_states[user_id].semester
    
    if subject not in AVAILABLE_SUBJECTS[semester]:
        bot.answer_callback_query(call.id, "Invalid subject. Please try again.")
        return
    
    user_states[user_id].subject = subject
    
    # Load the subject file
    with open(f"{semester}/{subject}.json", 'r') as f:
        subject_data = json.load(f)
    
    # Create inline keyboard with unit options
    markup = types.InlineKeyboardMarkup(row_width=2)
    unit_buttons = [
        types.InlineKeyboardButton(f"Unit {i+1}", callback_data=f"unit_{i+1}") 
        for i in range(len(subject_data['units']))
    ]
    markup.add(*unit_buttons)
    
    # Delete previous message
    delete_previous_message(chat_id)
    
    # Send new message and store its ID
    sent_msg = bot.send_message(chat_id, "Please select a unit:", reply_markup=markup)
    last_messages[chat_id] = sent_msg.message_id
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('unit_'))
def handle_unit_selection(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    unit_number = call.data[5:]  # Remove 'unit_' prefix
    unit_key = f"unit_{unit_number}"
    
    state = user_states[user_id]
    
    # Load questions from the selected unit
    with open(f"{state.semester}/{state.subject}.json", 'r') as f:
        subject_data = json.load(f)
    
    if unit_key not in subject_data['units']:
        bot.answer_callback_query(call.id, "Invalid unit. Please try again.")
        return
    
    # Select 10 random questions
    all_questions = subject_data['units'][unit_key]['mcqs']
    selected_questions = random.sample(all_questions, min(10, len(all_questions)))
    
    state.unit = unit_key
    state.questions = selected_questions
    state.start_time = datetime.now()
    
    # Delete previous message
    delete_previous_message(chat_id)
    
    # Start asking questions
    ask_question(call.message)
    
    bot.answer_callback_query(call.id)

def ask_question(message):
    user_id = message.chat.id
    chat_id = message.chat.id
    state = user_states[user_id]
    
    if state.current_question >= len(state.questions):
        show_final_score(message)
        return
    
    question = state.questions[state.current_question]
    options = question['options']
    
    # Create inline keyboard with options
    markup = types.InlineKeyboardMarkup(row_width=1)
    option_buttons = [
        types.InlineKeyboardButton(opt, callback_data=f"ans_{opt}")
        for opt in options
    ]
    markup.add(*option_buttons)
    
    # Delete previous message
    delete_previous_message(chat_id)
    
    # Send question with options
    question_text = f"Question {state.current_question + 1}/10:\n\n{question['question']}"
    sent_msg = bot.send_message(chat_id, question_text, reply_markup=markup)
    last_messages[chat_id] = sent_msg.message_id

@bot.callback_query_handler(func=lambda call: call.data.startswith('ans_'))
def handle_answer(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    state = user_states[user_id]
    
    user_answer = call.data[4:]  # Remove 'ans_' prefix
    current_question = state.questions[state.current_question]
    correct_answer = current_question['correct_answer']
    
    # Check if answer is correct
    if user_answer == correct_answer:
        state.score += 1
        feedback = "✅ Correct!"
    else:
        feedback = f"❌ Wrong! The correct answer is: {correct_answer}"
    
    # Delete previous message
    delete_previous_message(chat_id)
    
    # Send feedback
    sent_msg = bot.send_message(chat_id, feedback)
    last_messages[chat_id] = sent_msg.message_id
    
    # Move to next question
    state.current_question += 1
    bot.answer_callback_query(call.id)
    
    # Wait a moment before showing next question
    bot.delete_message(chat_id, sent_msg.message_id)
    ask_question(call.message)

def show_final_score(message):
    user_id = message.chat.id
    chat_id = message.chat.id
    state = user_states[user_id]
    
    # Calculate time taken
    time_taken = datetime.now() - state.start_time
    minutes = int(time_taken.total_seconds() // 60)
    seconds = int(time_taken.total_seconds() % 60)
    
    # Update user statistics
    if user_id not in user_scores:
        user_scores[user_id] = {
            'total_quizzes': 0,
            'total_score': 0,
            'highest_score': 0
        }
    
    user_scores[user_id]['total_quizzes'] += 1
    user_scores[user_id]['total_score'] += state.score
    user_scores[user_id]['highest_score'] = max(user_scores[user_id]['highest_score'], state.score)
    
    # Create result message
    result_message = (
        f"🎯 Quiz Completed!\n\n"
        f"Subject: {state.subject}\n"
        f"Unit: {state.unit}\n"
        f"Score: {state.score}/10\n"
        f"Time taken: {minutes}m {seconds}s\n\n"
    )
    
    # Add performance message
    if state.score == 10:
        result_message += "🏆 Perfect score! Outstanding performance!"
    elif state.score >= 8:
        result_message += "🌟 Excellent work!"
    elif state.score >= 6:
        result_message += "👍 Good job! Keep practicing!"
    else:
        result_message += "📚 Keep studying! You'll do better next time!"
    
    # Add suggestion for next action
    result_message += "\n\nSend /quiz to try another quiz or /stats to view your statistics!"
    
    # Delete previous message
    delete_previous_message(chat_id)
    
    # Send final score
    sent_msg = bot.send_message(chat_id, result_message)
    last_messages[chat_id] = sent_msg.message_id
    
    # Clear user state
    del user_states[user_id]

# Start the bot
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling() 
