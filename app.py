"""
公司官网 - Flask 主应用
功能：公司介绍、证书查询、在线考试、证书照片上传 + OCR
"""
import json
import sqlite3
import os
import uuid
import secrets
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'company-website-secret-key-change-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# 上传配置
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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


def admin_required(f):
    """要求管理员权限的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth_login', next=request.path))
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],))
        user = cursor.fetchone()
        conn.close()
        if not user or not user['is_admin']:
            return '无权访问，需要管理员权限', 403
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """获取当前登录用户信息"""
    if 'user_id' not in session:
        return None
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, phone, is_admin FROM users WHERE id = ?', (session['user_id'],))
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
@login_required
def exam():
    """在线考试页面（需登录）"""
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
    has_access = False
    if user:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM user_permissions WHERE user_id = ? AND resource_type = 'course' AND resource_value = ?",
            (user['id'], str(course_id))
        )
        has_access = cursor.fetchone() is not None
        conn.close()

    return render_template('course-detail.html',
                           course=dict(course),
                           chapters=chapters,
                           user=user,
                           has_access=has_access)


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

    # 检查权限（替代原来的购买检查）
    user_id = session['user_id']
    cursor.execute(
        "SELECT id FROM user_permissions WHERE user_id = ? AND resource_type = 'course' AND resource_value = ?",
        (user_id, str(course_id))
    )
    has_access = cursor.fetchone() is not None

    if not has_access:
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
    """个人中心：我的课程和考试权限"""
    conn = get_db()
    cursor = conn.cursor()

    # 查询用户有权限的课程
    cursor.execute('''
        SELECT c.id, c.title, c.description,
               (SELECT COUNT(*) FROM chapters WHERE course_id = c.id) as chapters_count
        FROM user_permissions up
        JOIN courses c ON up.resource_value = CAST(c.id AS TEXT) AND up.resource_type = 'course'
        WHERE up.user_id = ?
        ORDER BY up.created_at DESC
    ''', (session['user_id'],))
    courses = [dict(row) for row in cursor.fetchall()]

    # 查询用户有权限的考试
    cursor.execute(
        "SELECT resource_value FROM user_permissions WHERE user_id = ? AND resource_type = 'exam' ORDER BY created_at DESC",
        (session['user_id'],)
    )
    exams = [row['resource_value'] for row in cursor.fetchall()]

    conn.close()

    user = get_current_user()
    return render_template('user-orders.html', courses=courses, exams=exams, user=user)


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
                    'qualification_type': row['qualification_type'] or row['cert_name'],
                    'issue_date': row['issue_date'],
                    'expire_date': row['expire_date'] or '长期有效',
                    'status': row['status'],
                    'photo_url': row['photo_path'] or None,
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

@app.route('/api/exam/types')
def get_exam_types():
    """获取所有考试类型及题目数量（含零题目类型），标记用户权限"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT et.category, et.pass_score, COUNT(q.id) as cnt
            FROM exam_types et
            LEFT JOIN questions q ON et.category = q.category
            GROUP BY et.category
            ORDER BY et.sort_order
        ''')
        rows = cursor.fetchall()

        # 查询当前用户的考试权限
        user = get_current_user()
        user_exam_perms = set()
        if user:
            cursor.execute(
                "SELECT resource_value FROM user_permissions WHERE user_id = ? AND resource_type = 'exam'",
                (user['id'],)
            )
            user_exam_perms = {row['resource_value'] for row in cursor.fetchall()}
        conn.close()

        # 考试类型 → 图片文件名映射（按 sort_order 顺序）
        exam_images = [
            'exam_01_iso9001.png',    # ISO9001
            'exam_02_iso14001.png',   # ISO14001
            'exam_03_iso45001.png',   # ISO45001
            'exam_04_iatf16949.jpg',  # IATF16949
            'exam_05_vda63.png',      # VDA6.3
            'exam_06_vda65.png',      # VDA6.5
            'exam_07_iso13485.jpg',   # ISO13485
            'exam_08_qc080000.png',   # QC080000
            None,                      # ESG（缺图）
            'exam_10_calibration.jpg', # 计量校准
        ]
        types = []
        for i, row in enumerate(rows):
            img = exam_images[i] if i < len(exam_images) else None
            types.append({
                'category': row['category'],
                'count': row['cnt'],
                'pass_score': row['pass_score'],
                'image': f'/static/images/exams/{img}' if img else None,
                'has_permission': row['category'] in user_exam_perms,
            })

        return jsonify({'success': True, 'types': types})

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取考试类型失败：{str(e)}'})


@app.route('/api/exam/questions')
@login_required
def get_questions():
    """获取随机 50 题，每题 2 分，支持按考试类型筛选（需考试权限）"""
    category = request.args.get('category', '').strip()

    try:
        conn = get_db()
        cursor = conn.cursor()

        # 检查考试权限
        user = get_current_user()
        if category:
            cursor.execute(
                "SELECT id FROM user_permissions WHERE user_id = ? AND resource_type = 'exam' AND resource_value = ?",
                (user['id'], category)
            )
            if not cursor.fetchone():
                conn.close()
                return jsonify({'success': False, 'message': '您没有该考试类型的权限，请联系垚博企管开通'})

        if category:
            cursor.execute(
                'SELECT * FROM questions WHERE category = ? ORDER BY RANDOM() LIMIT 50',
                (category,)
            )
        else:
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
@login_required
def submit_exam():
    """提交考试答案并自动评分（需登录）"""
    data = request.get_json()
    # 考生姓名：优先使用登录用户名
    exam_taker = data.get('exam_taker', '').strip()
    user = get_current_user()
    if not exam_taker and user:
        exam_taker = user.get('username', '匿名考生')
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
            INSERT INTO exam_records (user_id, exam_taker, score, total_questions, correct_count, answers, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user['id'] if user else None,
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
# 证书上传 + OCR 路由
# ==========================================

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/admin/upload-cert')
@admin_required
def admin_upload_cert():
    """证书上传管理页面"""
    return render_template('admin-upload.html')


@app.route('/api/admin/certificate/upload', methods=['POST'])
@admin_required
def api_upload_certificate():
    """
    证书上传 API
    - 第一阶段：上传图片 → OCR 识别 → 返回提取结果（不保存）
    - 第二阶段：确认后 → 存入数据库
    """
    # ========== 第二阶段：确认保存 ==========
    if request.is_json:
        data = request.get_json()
        if data.get('confirmed'):
            name = (data.get('name') or '').strip()
            id_number = (data.get('id_number') or '').strip()
            cert_number = (data.get('cert_number') or '').strip()
            qualification_type = (data.get('qualification_type') or '').strip()
            issue_date = (data.get('issue_date') or '').strip()
            expire_date = (data.get('expire_date') or '').strip() or None
            photo_url = (data.get('photo_url') or '').strip()

            # 校验
            if not all([name, id_number, cert_number, qualification_type, issue_date]):
                return jsonify({'success': False, 'message': '请填写所有必填字段'})

            # 生成证书名称（资质类型 + 课程）
            cert_name = qualification_type

            # 自动判断状态
            status = '有效'
            if expire_date:
                try:
                    exp_dt = datetime.strptime(expire_date, '%Y-%m-%d')
                    if exp_dt < datetime.now():
                        status = '过期'
                except ValueError:
                    pass

            try:
                conn = get_db()
                cursor = conn.cursor()

                # 检查证书编号是否已存在
                cursor.execute('SELECT id FROM certificates WHERE cert_number = ?', (cert_number,))
                if cursor.fetchone():
                    conn.close()
                    return jsonify({'success': False, 'message': f'证书编号 {cert_number} 已存在，请勿重复上传'})

                cursor.execute('''
                    INSERT INTO certificates (name, id_number, cert_name, cert_number,
                                             qualification_type, issue_date, expire_date,
                                             status, photo_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (name, id_number, cert_name, cert_number,
                      qualification_type, issue_date, expire_date,
                      status, photo_url))
                conn.commit()
                conn.close()

                return jsonify({'success': True, 'message': f'证书 {cert_number} 已成功入库！'})

            except Exception as e:
                return jsonify({'success': False, 'message': f'保存失败：{str(e)}'})

    # ========== 第一阶段：上传图片 + OCR ==========
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': '请选择证书照片'})

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'message': '请选择证书照片'})

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': '仅支持 JPG / PNG 格式'})

    try:
        # 保存上传文件
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"cert_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # 调用 OCR
        from utils.ocr import extract_text, parse_certificate_info
        raw_text = extract_text(filepath)
        info = parse_certificate_info(raw_text)

        # 照片的 URL 路径
        photo_url = f'/static/uploads/{filename}'

        return jsonify({
            'success': True,
            'photo_url': photo_url,
            'raw_text': raw_text,
            'ocr_result': {
                'name': info.get('name', ''),
                'id_number': info.get('id_number', ''),
                'cert_number': info.get('cert_number', ''),
                'qualification_type': info.get('qualification_type', ''),
                'issue_date': info.get('issue_date', ''),
                'expire_date': info.get('expire_date', ''),
                'status': info.get('status', '有效'),
            }
        })

    except ImportError as e:
        return jsonify({'success': False, 'message': f'OCR 依赖未安装：{str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败：{str(e)}'})


# ==========================================
# 管理员 - 用户权限管理
# ==========================================

@app.route('/admin/users')
@admin_required
def admin_users():
    """用户权限管理页面"""
    return render_template('admin-users.html')


@app.route('/api/admin/users/list')
@admin_required
def api_admin_users_list():
    """获取所有用户及其权限"""
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute('SELECT id, username, phone, is_admin, created_at FROM users ORDER BY created_at DESC')
        users = [dict(row) for row in cursor.fetchall()]

        # 获取每个用户的权限
        for u in users:
            cursor.execute(
                "SELECT resource_type, resource_value FROM user_permissions WHERE user_id = ?",
                (u['id'],)
            )
            perms = cursor.fetchall()
            u['permissions'] = [{'type': p['resource_type'], 'value': p['resource_value']} for p in perms]

        # 获取所有课程列表（供权限分配用）
        cursor.execute("SELECT id, title FROM courses WHERE status = 'published' ORDER BY sort_order")
        courses = [dict(row) for row in cursor.fetchall()]

        # 获取所有考试类型
        cursor.execute('SELECT category FROM exam_types ORDER BY sort_order')
        exam_types = [row['category'] for row in cursor.fetchall()]

        conn.close()

        return jsonify({
            'success': True,
            'users': users,
            'courses': courses,
            'exam_types': exam_types,
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取用户列表失败：{str(e)}'})


@app.route('/api/admin/permissions/grant', methods=['POST'])
@admin_required
def api_admin_grant_permission():
    """授予权限"""
    data = request.get_json()
    user_id = data.get('user_id')
    resource_type = data.get('resource_type')
    resource_value = data.get('resource_value')

    if not all([user_id, resource_type, resource_value]):
        return jsonify({'success': False, 'message': '参数不完整'})

    if resource_type not in ('course', 'exam'):
        return jsonify({'success': False, 'message': '无效的权限类型'})

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR IGNORE INTO user_permissions (user_id, resource_type, resource_value, granted_by) VALUES (?, ?, ?, ?)',
            (user_id, resource_type, resource_value, session['user_id'])
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '权限已授予'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'授权失败：{str(e)}'})


@app.route('/api/admin/permissions/revoke', methods=['POST'])
@admin_required
def api_admin_revoke_permission():
    """撤销权限"""
    data = request.get_json()
    user_id = data.get('user_id')
    resource_type = data.get('resource_type')
    resource_value = data.get('resource_value')

    if not all([user_id, resource_type, resource_value]):
        return jsonify({'success': False, 'message': '参数不完整'})

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            'DELETE FROM user_permissions WHERE user_id = ? AND resource_type = ? AND resource_value = ?',
            (user_id, resource_type, resource_value)
        )
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '权限已撤销'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'撤权失败：{str(e)}'})


# ==========================================
# SEO 路由：robots.txt 和 sitemap.xml
# ==========================================

@app.route('/robots.txt')
def robots_txt():
    """返回 robots.txt 引导搜索引擎爬取"""
    return app.send_static_file('robots.txt')


@app.route('/sitemap.xml')
def sitemap_xml():
    """返回 sitemap.xml 站点地图"""
    return app.send_static_file('sitemap.xml')


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
        app.run(debug=True, host='0.0.0.0', port=5000)
