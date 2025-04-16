from flask import Flask, render_template, request, session, redirect, url_for , jsonify
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
    vocab_list = session.get('vocab_list', [])
    recent_vocab = vocab_list[-5:]  # 최근 5개 단어
    return render_template('index.html', recent_vocab=recent_vocab)



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

    # 모든 문제 다 풀었으면 결과로 이동
    if current >= total:
        return redirect(url_for('result'))

    # ✅ 이전 문제의 결과 보여주는 단계
    if session.get('show_result'):
        feedback = session.pop('feedback')
        selected_choice = session.pop('selected')
        session.pop('show_result')

        show_result = True
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
            wait_next=True
        )

    # ✅ 사용자가 정답을 제출한 경우 (POST)
    elif request.method == 'POST':
        selected_choice = request.form.get('choice')
        correct_answer = questions[current]['answer']
        hiragana = questions[current].get('hiragana', '')

        if selected_choice == correct_answer:
            feedback = f"O - 정답입니다: '{correct_answer} {hiragana}'"
            session['score'] += 1
        else:
            feedback = f"X - 정답은 '{correct_answer} {hiragana}'입니다."

        # 기록 저장
        session['answers'].append({
            'question': questions[current]['question'],
            'selected': selected_choice,
            'correct': correct_answer,
            'hiragana': hiragana,
            'level': questions[current].get('level')
        })

        # 결과 보여줄 준비
        session['selected'] = selected_choice
        session['feedback'] = feedback
        session['show_result'] = True
        session['current'] += 1  # ✅ 이건 여기서 처리!

        return redirect(url_for('quiz'))

    # ✅ 기본 화면 (문제 풀기)
    question = questions[current]['question']
    choices = questions[current]['choices'][:]
    random.shuffle(choices)

    return render_template(
        'quiz.html',
        question=question,
        choices=choices,
        current=current,
        total=total,
        show_result=False,
        feedback='',
        selected_choice=None,
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

# --- 반드시 있어야 하는 라우트 ---
@app.route('/add-to-vocab', methods=['POST'])
def add_to_vocab():
    question = request.form.get('question')
    answer = request.form.get('answer')

    matched_answer = next(
        (a for a in session.get('answers', []) if a['question'] == question and a['correct'] == answer),
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
        'answer': answer,
        'hiragana': hiragana,
        'level': level,
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
