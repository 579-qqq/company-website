"""
公司官网 - Flask 主应用
功能：公司介绍、证书查询、在线考试
"""
import json
import sqlite3
import os
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'company-website-secret-key-change-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


@app.context_processor
def inject_user():
    """将所有模板注入 user 变量"""
    return {'user': get_current_user()}


# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'company.db')


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ==========================================
# 认证装饰器
# ==========================================

def login_required(f):
    """要求登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """获取当前登录用户信息"""
    if 'user_id' not in session:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, phone FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


# ==========================================
# 页面路由
# ==========================================

@app.route('/')
def index():
    """首页 - 公司介绍"""
    return render_template('index.html')


@app.route('/about')
def about():
    """关于我们"""
    return render_template('about.html')


@app.route('/services')
def services():
    """核心业务"""
    return render_template('services.html')


@app.route('/training')
def training():
    """培训课程"""
    return render_template('training.html')


@app.route('/certificate')
def certificate():
    """证书查询页面"""
    return render_template('certificate.html')


@app.route('/exam')
def exam():
    """在线考试页面"""
    return render_template('exam.html')


@app.route('/about/team')
def about_team():
    """核心团队详情"""
    return render_template('about-team.html')


@app.route('/services/consulting')
def services_consulting():
    """管理咨询"""
    return render_template('services-consulting.html')


@app.route('/services/certification')
def services_certification():
    """体系认证"""
    return render_template('services-certification.html')


@app.route('/gallery/training')
def gallery_training():
    """培训实景"""
    return render_template('gallery-training.html')


@app.route('/gallery/collaboration')
def gallery_collaboration():
    """合作实景"""
    return render_template('gallery-collaboration.html')


# ==========================================
# 认证路由（页面 + API）
# ==========================================

@app.route('/auth/login')
def auth_login():
    """登录页面"""
    return render_template('auth-login.html')


@app.route('/auth/register')
def auth_register():
    """注册页面"""
    return render_template('auth-register.html')


@app.route('/auth/logout')
def auth_logout():
    """退出登录"""
    session.clear()
    return redirect(url_for('index'))


@app.route('/api/auth/register', methods=['POST'])
def api_register():
    """注册API"""
    data = request.get_json()
    username = (data.get('username') or '').strip()
    phone = (data.get('phone') or '').strip()
    password = data.get('password', '')

    if not username or not phone or not password:
        return jsonify({'success': False, 'message': '请填写所有必填字段'})
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少6位'})
    if not phone.isdigit() or len(phone) != 11:
        return jsonify({'success': False, 'message': '请输入正确的11位手机号'})

    try:
        conn = get_db()
        cursor = conn.cursor()
        # 检查手机号是否已注册
        cursor.execute('SELECT id FROM users WHERE phone = ?', (phone,))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': '该手机号已注册，请直接登录'})

        password_hash = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO users (username, phone, password_hash) VALUES (?, ?, ?)',
            (username, phone, password_hash)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        # 注册成功自动登录
        session['user_id'] = user_id
        session['username'] = username

        return jsonify({'success': True, 'message': '注册成功！'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'注册失败：{str(e)}'})


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """登录API"""
    data = request.get_json()
    phone = (data.get('phone') or '').strip()
    password = data.get('password', '')

    if not phone or not password:
        return jsonify({'success': False, 'message': '请输入手机号和密码'})

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({'success': False, 'message': '账号不存在，请先注册'})

        if not check_password_hash(user['password_hash'], password):
            return jsonify({'success': False, 'message': '密码错误，请重试'})

        session['user_id'] = user['id']
        session['username'] = user['username']

        return jsonify({'success': True, 'message': '登录成功！'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败：{str(e)}'})


# ==========================================
# 课程路由
# ==========================================

@app.route('/courses')
def courses_list():
    """课程列表页"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM courses WHERE status = 'published' ORDER BY sort_order"
    )
    courses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    user = get_current_user()
    return render_template('courses.html', courses=courses, user=user)


@app.route('/courses/<int:course_id>')
def course_detail(course_id):
    """课程详情页"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,))
    course = cursor.fetchone()
    if not course:
        conn.close()
        return '课程不存在', 404

    cursor.execute(
        'SELECT * FROM chapters WHERE course_id = ? ORDER BY sort_order',
        (course_id,)
    )
    chapters = [dict(row) for row in cursor.fetchall()]
    conn.close()

    user = get_current_user()
    has_paid = False
    if user:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM orders WHERE user_id = ? AND course_id = ? AND status = 'paid'",
            (user['id'], course_id)
        )
        has_paid = cursor.fetchone() is not None
        conn.close()

    return render_template('course-detail.html',
                           course=dict(course),
                           chapters=chapters,
                           user=user,
                           has_paid=has_paid)


@app.route('/courses/<int:course_id>/watch/<int:chapter_id>')
@login_required
def course_watch(course_id, chapter_id):
    """视频观看页 — 需登录且已购买"""
    conn = get_db()
    cursor = conn.cursor()

    # 查课程
    cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,))
    course = cursor.fetchone()
    if not course:
        conn.close()
        return '课程不存在', 404

    # 检查购买（免费章节可免检？不，整课购买制）
    user_id = session['user_id']
    cursor.execute(
        "SELECT id FROM orders WHERE user_id = ? AND course_id = ? AND status = 'paid'",
        (user_id, course_id)
    )
    has_paid = cursor.fetchone() is not None

    if not has_paid:
        conn.close()
        return redirect(url_for('course_detail', course_id=course_id))

    # 查章节
    cursor.execute('SELECT * FROM chapters WHERE id = ? AND course_id = ?', (chapter_id, course_id))
    chapter = cursor.fetchone()
    if not chapter:
        conn.close()
        return '章节不存在', 404

    # 获取该课程所有章节（导航用）
    cursor.execute(
        'SELECT * FROM chapters WHERE course_id = ? ORDER BY sort_order',
        (course_id,)
    )
    chapters = [dict(row) for row in cursor.fetchall()]
    conn.close()

    user = get_current_user()
    return render_template('course-watch.html',
                           course=dict(course),
                           chapter=dict(chapter),
                           chapters=chapters,
                           user=user)


# ==========================================
# 支付 API
# ==========================================

@app.route('/api/payment/create', methods=['POST'])
@login_required
def api_create_payment():
    """创建订单 — 价格从数据库读取，不信任客户端"""
    data = request.get_json()
    course_id = data.get('course_id')

    if not course_id:
        return jsonify({'success': False, 'message': '参数错误'})

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 价格从数据库读取
        cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,))
        course = cursor.fetchone()
        if not course:
            conn.close()
            return jsonify({'success': False, 'message': '课程不存在'})

        user_id = session['user_id']

        # 检查是否已购买
        cursor.execute(
            "SELECT id FROM orders WHERE user_id = ? AND course_id = ? AND status = 'paid'",
            (user_id, course_id)
        )
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'message': '您已购买过该课程'})

        # 检查是否有待支付订单
        cursor.execute(
            "SELECT id, order_no FROM orders WHERE user_id = ? AND course_id = ? AND status = 'pending'",
            (user_id, course_id)
        )
        pending = cursor.fetchone()
        if pending:
            conn.close()
            return jsonify({
                'success': True,
                'order_no': pending['order_no'],
                'amount': course['price'],
                'reuse': True
            })

        # 生成订单号
        order_no = datetime.now().strftime('%Y%m%d%H%M%S') + secrets.token_hex(4)
        amount = course['price']

        cursor.execute(
            'INSERT INTO orders (order_no, user_id, course_id, amount) VALUES (?, ?, ?, ?)',
            (order_no, user_id, course_id, amount)
        )
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'order_no': order_no,
            'amount': amount,
            'course_title': course['title']
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'创建订单失败：{str(e)}'})


@app.route('/api/payment/status/<order_no>')
@login_required
def api_payment_status(order_no):
    """查询订单支付状态"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE order_no = ? AND user_id = ?',
            (order_no, session['user_id'])
        )
        order = cursor.fetchone()
        conn.close()

        if not order:
            return jsonify({'success': False, 'message': '订单不存在'})

        return jsonify({
            'success': True,
            'order_no': order['order_no'],
            'status': order['status'],
            'amount': order['amount'],
            'course_id': order['course_id']
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/payment/mock-pay', methods=['POST'])
@login_required
def api_mock_pay():
    """模拟支付（仅开发测试用，上线后删除）"""
    data = request.get_json()
    order_no = data.get('order_no')

    if not order_no:
        return jsonify({'success': False, 'message': '缺少订单号'})

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM orders WHERE order_no = ? AND user_id = ?",
            (order_no, session['user_id'])
        )
        order = cursor.fetchone()

        if not order:
            conn.close()
            return jsonify({'success': False, 'message': '订单不存在'})

        if order['status'] != 'pending':
            conn.close()
            return jsonify({'success': False, 'message': '订单状态异常'})

        cursor.execute(
            "UPDATE orders SET status = 'paid', payment_method = 'mock', transaction_id = ?, paid_at = ? WHERE order_no = ?",
            (f'mock_{secrets.token_hex(8)}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_no)
        )
        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '支付成功！', 'course_id': order['course_id']})

    except Exception as e:
        return jsonify({'success': False, 'message': f'支付失败：{str(e)}'})


@app.route('/api/payment/callback', methods=['POST'])
def api_payment_callback():
    """微信支付回调通知（需真实商户号才能工作）"""
    body = request.get_data()

    # TODO: 接入真实商户号后，在此验证微信签名
    # signature = request.headers.get('Wechatpay-Signature')
    # ...

    try:
        data = json.loads(body)
        order_no = data.get('out_trade_no')
        transaction_id = data.get('transaction_id')
        callback_amount = data.get('amount', {}).get('total', 0)

        if not order_no:
            return jsonify({'code': 'FAIL', 'message': '缺少订单号'}), 400

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE order_no = ?', (order_no,))
        order = cursor.fetchone()

        if not order:
            conn.close()
            return jsonify({'code': 'FAIL', 'message': '订单不存在'}), 404

        # 金额校验
        if order['amount'] != callback_amount:
            conn.close()
            return jsonify({'code': 'FAIL', 'message': '金额不匹配'}), 400

        # 防重复处理
        if order['status'] == 'paid':
            conn.close()
            return jsonify({'code': 'SUCCESS'}), 200

        # 更新订单
        cursor.execute(
            "UPDATE orders SET status = 'paid', payment_method = 'wechat', transaction_id = ?, paid_at = ? WHERE order_no = ?",
            (transaction_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), order_no)
        )
        conn.commit()
        conn.close()

        return jsonify({'code': 'SUCCESS'}), 200

    except Exception as e:
        return jsonify({'code': 'FAIL', 'message': str(e)}), 500


# ==========================================
# 用户路由
# ==========================================

@app.route('/user/orders')
@login_required
def user_orders():
    """我的订单"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT o.*, c.title as course_title
           FROM orders o
           LEFT JOIN courses c ON o.course_id = c.id
           WHERE o.user_id = ?
           ORDER BY o.created_at DESC''',
        (session['user_id'],)
    )
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()

    user = get_current_user()
    return render_template('user-orders.html', orders=orders, user=user)


# ==========================================
# 证书查询 API
# ==========================================

@app.route('/api/certificate/query', methods=['POST'])
def query_certificate():
    """查询证书：根据姓名和身份证号"""
    data = request.get_json()
    name = data.get('name', '').strip()
    id_number = data.get('id_number', '').strip()

    if not name or not id_number:
        return jsonify({'success': False, 'message': '请填写姓名和身份证号码'})

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM certificates WHERE name = ? AND id_number = ? ORDER BY issue_date DESC',
            (name, id_number)
        )
        results = cursor.fetchall()
        conn.close()

        if results:
            cert_list = []
            for row in results:
                cert_list.append({
                    'id': row['id'],
                    'cert_name': row['cert_name'],
                    'cert_number': row['cert_number'],
                    'issue_date': row['issue_date'],
                    'expire_date': row['expire_date'] or '长期有效',
                    'status': row['status']
                })
            return jsonify({
                'success': True,
                'name': name,
                'certificates': cert_list,
                'count': len(cert_list)
            })
        else:
            return jsonify({
                'success': False,
                'message': f'未找到 {name} 的相关证书记录，请检查姓名和身份证号码是否正确'
            })

    except Exception as e:
        return jsonify({'success': False, 'message': f'查询出错：{str(e)}'})


# ==========================================
# 考试系统 API
# ==========================================

@app.route('/api/exam/questions')
def get_questions():
    """获取随机 50 题，每题 2 分"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        # 从题库随机取 50 题
        cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 50')
        rows = cursor.fetchall()
        conn.close()

        questions = []
        for row in rows:
            questions.append({
                'id': row['id'],
                'category': row['category'],
                'question_type': row['question_type'],
                'content': row['content'],
                'options': json.loads(row['options']),
                'score': 2  # 统一每题 2 分
            })

        return jsonify({
            'success': True,
            'questions': questions,
            'total': len(questions)
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取题目失败：{str(e)}'})


@app.route('/api/exam/submit', methods=['POST'])
def submit_exam():
    """提交考试答案并自动评分"""
    data = request.get_json()
    exam_taker = data.get('exam_taker', '匿名考生')
    answers = data.get('answers', {})

    if not answers:
        return jsonify({'success': False, 'message': '请先作答再提交'})

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 只评分考生抽到的题目
        question_ids = list(answers.keys())
        placeholders = ','.join(['?'] * len(question_ids))
        cursor.execute(f'SELECT * FROM questions WHERE id IN ({placeholders})', question_ids)
        questions = cursor.fetchall()

        # 评分
        total_score = 0
        correct_count = 0
        total_questions = len(questions)
        details = []

        for q in questions:
            qid = str(q['id'])
            user_answer = answers.get(qid, '')
            is_correct = user_answer == q['answer']

            if is_correct:
                total_score += 2  # 每题 2 分
                correct_count += 1

            details.append({
                'question_id': q['id'],
                'content': q['content'],
                'user_answer': user_answer,
                'correct_answer': q['answer'],
                'is_correct': is_correct,
                'score': 2
            })

        # 保存考试记录
        cursor.execute('''
            INSERT INTO exam_records (exam_taker, score, total_questions, correct_count, answers, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            exam_taker,
            total_score,
            total_questions,
            correct_count,
            json.dumps(answers, ensure_ascii=False),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'exam_taker': exam_taker,
            'score': total_score,
            'total_questions': total_questions,
            'correct_count': correct_count,
            'max_score': 100,
            'pass_score': 70,
            'details': details,
            'message': f'{exam_taker}，您答对了 {correct_count}/{total_questions} 题，得分 {total_score} 分！'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'提交失败：{str(e)}'})


# ==========================================
# 启动应用
# ==========================================

if __name__ == '__main__':
    # 检查数据库是否存在
    if not os.path.exists(DB_PATH):
        print("[WARNING] 数据库不存在，请先运行: python database/init_db.py")
    else:
        print("[OK] 垚博企管官网启动...")
        print("   - 访问地址: http://127.0.0.1:5000")
        print("   - 按 Ctrl+C 停止服务器")
        app.run(debug=True, host='127.0.0.1', port=5000)
