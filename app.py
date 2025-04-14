from flask import Flask, render_template, request, session, redirect, url_for
import random
import json
from datetime import datetime

# ----------------------------------
# 📌 앱 환경 설정
# ----------------------------------
app = Flask(__name__)
app.secret_key = 'your-secret-key'

# 문제 데이터 불러오기
def load_quiz_data():
    with open('data/quiz.json', 'r', encoding='utf-8') as f:
        return json.load(f)

ALL_DATA = load_quiz_data()


# ----------------------------------
# 🏠 메인 페이지 및 레벨/문제수 선택
# ----------------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        session['level'] = request.form.get('level')
        return redirect(url_for('select_count'))
    return render_template('start.html')

@app.route('/select-count', methods=['GET', 'POST'])
def select_count():
    if request.method == 'POST':
        value = request.form.get('num_questions')
        if not value:
            return "문제 수를 선택해주세요.", 400

        session['num_questions'] = int(value)
        session['current'] = 0
        session['score'] = 0
        session['answers'] = []

        # 선택한 레벨에 맞는 문제 추출
        level = session['level']
        filtered = [q for q in ALL_DATA if q.get('level') == level]
        random.shuffle(filtered)

        if len(filtered) < session['num_questions']:
            return "선택한 레벨에 해당하는 문제가 부족합니다.", 400

        session['questions'] = filtered[:session['num_questions']]
        return redirect(url_for('quiz'))

    return render_template('select_count.html')


# ----------------------------------
# 🧠 퀴즈 풀이
# ----------------------------------
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    current = session.get('current', 0)
    total = session.get('num_questions', 5)
    questions = session.get('questions', [])

    if current >= total:
        return redirect(url_for('result'))

    show_result = False
    feedback = ''
    selected_choice = None

    if session.get('show_result'):
        feedback = session.pop('feedback')
        selected_choice = session.pop('selected')
        show_result = True
        session.pop('show_result')
        session['current'] += 1

        return render_template(
            'quiz.html',
            question=questions[current]['question'],
            choices=questions[current]['choices'],
            current=current,
            total=total,
            show_result=show_result,
            feedback=feedback,
            selected_choice=selected_choice,
            wait_next=True
        )


    elif request.method == 'POST':

        selected_choice = request.form.get('choice')

        correct_answer = questions[current]['answer']

        correct_answer_text = correct_answer

        hiragana = questions[current].get('hiragana', '')

        if selected_choice == correct_answer_text:

            feedback = f"O - 정답입니다: '{correct_answer} {hiragana}'"

            session['score'] += 1

        else:

            feedback = f"X - 정답은 '{correct_answer} {hiragana}'입니다."

        session['selected'] = selected_choice
        session['feedback'] = feedback
        session['show_result'] = True

        # 정답 기록 (이거 없으면 결과에 아무 것도 안 나와!)
        session['answers'].append({
            'question': questions[current]['question'],
            'selected': selected_choice,
            'correct': correct_answer,
            'hiragana': hiragana,
            'level': questions[current].get('level')
        })

        return redirect(url_for('quiz'))

    # GET 요청 처리
    question = questions[current]['question']
    choices = questions[current]['choices'][:]
    random.shuffle(choices)

    return render_template(
        'quiz.html',
        question=question,
        choices=choices,
        current=current,
        total=total,
        show_result=show_result,
        feedback=feedback,
        selected_choice=selected_choice,
        wait_next=False
    )


# ----------------------------------
# 🏁 퀴즈 결과
# ----------------------------------
@app.route('/result')
def result():
    print("[DEBUG] answers:", session.get('answers'))
    return render_template(
        'result.html',
        score=session.get('score', 0),
        total=session.get('num_questions', 0),
        answers=session.get('answers', [])
    )

@app.route('/retry-wrong')
def retry_wrong():
    wrong_answers = [
        {
            "question": item["question"],
            "choices": [item["correct"].split()[0], item["selected"], "1", "2"],  # 대충 채워줌 (나중에 개선)
            "answer": item["correct"].split()[0],  # 실제 답
            "hiragana": item.get("hiragana"),
            "level": item.get("level")
        }
        for item in session.get('answers', [])
        if item['selected'] != item['correct'].split()[0]
    ]

    if not wrong_answers:
        return "틀린 문제가 없어요! 🎉", 200

    # 새로운 퀴즈 세션 준비
    session['questions'] = wrong_answers
    session['num_questions'] = len(wrong_answers)
    session['current'] = 0
    session['score'] = 0
    session['answers'] = []

    return redirect(url_for('quiz'))


# ----------------------------------
# 📘 단어장 기능
# ----------------------------------
@app.route('/vocab')
def vocab():
    vocab_list = session.get('vocab_list', [])
    return render_template('vocab.html', vocab_list=vocab_list)

@app.route('/add-to-vocab', methods=['POST'])
def add_to_vocab():
    question = request.form.get('question')
    answer = request.form.get('answer').split()[0]  # ← 핵심: '먹다 たべる' → '먹다'

    matched_answer = next(
        (a for a in session.get('answers', []) if a['question'] == question and a['correct'].split()[0] == answer),
        None
    )

    if matched_answer:
        level = matched_answer.get('level', 'N/A')
        hiragana = matched_answer.get('hiragana', '')
    else:
        level = session.get('level', 'N/A')
        hiragana = ''

    new_item = {
        'question': question,
        'answer': answer,               # "먹다"
        'hiragana': hiragana,           # "たべる"
        'level': level,
        'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # (선택) 추가일도 넣기
    }

    vocab_list = session.get('vocab_list', [])
    if new_item not in vocab_list:
        vocab_list.append(new_item)
        session['vocab_list'] = vocab_list

    return redirect(url_for('result'))
@app.route('/delete-vocab', methods=['POST'])
def delete_vocab():
    word = request.form.get('question')
    answer = request.form.get('answer')
    vocab_list = session.get('vocab_list', [])

    vocab_list = [item for item in vocab_list if not (item['question'] == word and item['answer'] == answer)]
    session['vocab_list'] = vocab_list
    return redirect(url_for('vocab'))

@app.route('/clear-vocab', methods=['POST'])
def clear_vocab():
    session['vocab_list'] = []
    return redirect(url_for('vocab'))


# ----------------------------------
# 🚀 서버 실행
# ----------------------------------
if __name__ == '__main__':
    app.run(debug=True) 