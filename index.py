from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import pymysql
from dotenv import load_dotenv
import os
from datetime import datetime  # datetime 모듈 추가
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# .env 파일 로드
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')  # 환경 변수에서 비밀 키를 읽어옴

# 데이터베이스 정보 처리하는 부분
db = pymysql.connect(
    host=os.getenv('DB_HOST'),
    port=int(os.getenv('DB_PORT')),
    user=os.getenv('DB_USER'),
    passwd=os.getenv('DB_PASSWORD'),
    db=os.getenv('DB_NAME'),
    charset='utf8'
)
cur = db.cursor()

# 게시글 좋아요 처리 라우터
@app.route('/likes/<int:post_id>', methods=['POST', 'GET'])
def like(post_id):
    if(request.method == 'GET'):
        sqlstring = """
        SELECT u.nickname, u.xid
        FROM post_like as pl
        JOIN user as u ON pl.user_xid = u.xid 
        WHERE pl.post_id = %s
        """
        cur.execute(sqlstring, post_id)
        result = cur.fetchall()
        print(result)
        return jsonify(result)
    else:
        user = session.get('user', None)
        if not user:
            return {'error': 'Unauthorized'}, 401  # 로그인이 되어있지 않으면 401 에러 반환
        comform = "SELECT * FROM post_like WHERE user_xid = %s AND post_id = %s"
        cur.execute(comform, (user[0], post_id))
        result = cur.fetchone()
        if result:
            sqlstring = "DELETE FROM post_like WHERE user_xid = %s AND post_id = %s"
            cur.execute(sqlstring, (user[0], post_id))
            db.commit()
            return {'result': 'success'}, 200

        else:
            created_at = datetime.now()
            sqlstring = "INSERT INTO post_like (user_xid, post_id, created_at) VALUES (%s, %s, %s)"
            cur.execute(sqlstring, (user[0], post_id, created_at))
            db.commit()

            return {'result': 'success'}, 200  # JSON 응답 반환

#사용자 정보 조회 라우터
@app.route('/users/<int:user_xid>', methods=['GET'])
def user_detail(user_xid):
    print(user_xid)

    # 사용자 정보 가져오기
    sqlstring = "SELECT * FROM user WHERE xid = %s"
    cur.execute(sqlstring, (user_xid,))
    user = cur.fetchone()

    if not user:
        return "사용자를 찾을 수 없습니다.", 404

    # 사용자가 작성한 게시글 가져오기
    query_posts = """
    SELECT post_id, title, created_at
    FROM post
    WHERE user_xid = %s
    ORDER BY created_at DESC
    """
    cur.execute(query_posts, (user_xid,))
    posts = cur.fetchall()

    # 사용자가 작성한 댓글 가져오기
    query_comments = """
    SELECT c.comment_id, c.content, p.title, c.created_at, c.post_id
    FROM comment c
    JOIN post p ON c.post_id = p.post_id
    WHERE c.user_xid = %s
    ORDER BY c.created_at DESC
    """
    cur.execute(query_comments, (user_xid,))
    comments = cur.fetchall()
    myProfile = user_xid == session.get('user', [None])[0]

    return render_template(
        'user_detail.html',
        user=user,
        posts=posts,
        comments=comments,
        myProfile=myProfile
    )
    
#사용자 정보 수정 라우터
@app.route('/users/edit/<int:user_xid>', methods=['GET','PATCH'])
def user_update(user_xid):
    # if 'user' not in session or session['user']['xid'] != user_xid:
    #     return redirect(url_for('login'))
    if request.method == 'PATCH':
        print("update")
        data = request.get_json()
        id = data.get('id')
        nickname = data.get('nickname')
        name = data.get('name')
        email = data.get('email')
        birth = data.get('birth')
        
        sqlstring = "UPDATE user SET user_id = %s, nickname = %s, name = %s, email = %s, birthdate = %s WHERE xid = %s"
        cur.execute(sqlstring, (id, nickname, name, email, birth, user_xid))
        db.commit()
        
        return {'result': 'success'}, 200
    

    if request.method == 'GET':
        sqlstring = "SELECT * FROM user WHERE xid = %s"
        cur.execute(sqlstring, user_xid)
        user = cur.fetchone()
        return render_template('user_edit.html', user=user)

#아이디 중복 검사 라우터
@app.route('/users/check-id', methods=['GET'])
def check_id():
    user_id = request.args.get('id')
    sqlstring = "SELECT COUNT(*) FROM user WHERE user_id = %s"
    cur.execute(sqlstring, (user_id,))
    result = cur.fetchone()
    print("api:",result)
    if result[0] > 0:
        return {"exists": True}  # 아이디 사용 가능
    return {"exists": False}  # 아이디 이미 존재함

#회원가입 요청 라우터
@app.route('/users', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        print("signup")
        id = request.form['id']
        password = request.form['password']
        nickname = request.form['nickname']
        email = request.form['email']
        created_at = datetime.now()  # 현재 시간을 생성
        
        # 데이터베이스에 사용자 정보 저장
        sqlstring = "INSERT INTO user (user_id, password, nickname, email, state, created_at) VALUES (%s, %s, %s, %s, 'activate', %s)"
        cur.execute(sqlstring, (id, password, nickname, email, created_at))
        db.commit()
        
        return redirect(url_for('login'))  # 회원가입 성공시 로그인 페이지로 이동
    return render_template('signup.html')

#계정 비활성화 요청 라우터
@app.route('/users/<int:user_xid>', methods=['PATCH'])
def deactivate(user_xid):
    print("deactivate")
    user = session.get('user', None)
    print(user)
    if user and user[0] == user_xid:
        print("deactivate")
        sqlstring = "UPDATE user SET state = 'deactivate' WHERE xid = %s"
        cur.execute(sqlstring, (user_xid,))
        db.commit()
        session.pop('user', None)
        return {'result': 'success'}, 200  # JSON 응답 반환
    return {'error': 'Unauthorized'}, 401

#로그인 요청 라우터
@app.route('/users/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 데이터베이스에서 계정 존재 확인
        sqlstring = "SELECT * FROM user WHERE user_id = %s AND password = %s AND state = 'activate'"
        cur.execute(sqlstring, (username, password))
        user = cur.fetchone()
        
        if user:
            session['user'] = user # 세션에 사용자 정보 저장
            return redirect(url_for('main')) # 로그인 성공시 메인 페이지로 이동
        else:
            return render_template('login.html', error='로그인에 실패하였습니다.')
    
    return render_template('login.html')

#로그아웃 요청 라우터
@app.route('/users/logout')
def logout():
    session.pop('user', None) # 세션에서 사용자 정보 삭제
    return redirect(url_for('main')) 


#주환님 코드 추가 ------------------------------------------------------
#추가
@app.route('/post/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))  # 로그인되지 않은 경우 로그인 페이지로 리다이렉트

    print("세션 데이터:", session['user'])

    user_xid = session['user'][0]  # 세션에서 사용자 ID 가져오기
    cur = db.cursor()

    # 이미 좋아요 눌렀는지 확인
    query_check = "SELECT 1 FROM post_like WHERE user_xid = %s AND post_id = %s"
    cur.execute(query_check, (user_xid, post_id))
    if cur.fetchone():
        query_unlike = "DELETE FROM post_like WHERE user_xid = %s AND post_id = %s"
        cur.execute(query_unlike, (user_xid, post_id))
    else:
        query_like = "INSERT INTO post_like (user_xid, post_id, created_at) VALUES (%s, %s, NOW())"
        cur.execute(query_like, (user_xid, post_id))
    db.commit()

    return redirect(url_for('post_detail', post_id=post_id))  # 상세 페이지로 리다이렉트

#추가 - 댓글 좋아요
@app.route('/comment/<int:comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    if 'user' not in session:
        return redirect(url_for('login'))  # 로그인되지 않은 경우 로그인 페이지로 리다이렉트

    user_xid = session['user'][0]  # 세션에서 사용자 ID 가져오기

    cur = db.cursor()
    # 이미 좋아요 눌렀는지 확인
    query_check = "SELECT 1 FROM comment_like WHERE user_xid = %s AND comment_comment_id = %s"
    cur.execute(query_check, (user_xid, comment_id))
    if cur.fetchone():
        query_unlike = "DELETE FROM comment_like WHERE user_xid = %s AND comment_comment_id = %s"
        cur.execute(query_unlike, (user_xid, comment_id))
    else:
        query_like = "INSERT INTO comment_like (user_xid, comment_comment_id, created_at) VALUES (%s, %s, NOW())"
        cur.execute(query_like, (user_xid, comment_id))
    db.commit()

    return redirect(request.referrer)  # 원래 페이지로 리다이렉트


#추가 - 게시글 삭제
@app.route('/post/<int:post_id>/delete', methods=['POST'])
def delete_post(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))  # 로그인 여부 확인

    cur = db.cursor()

    # 게시글 소유자 확인
    query_owner = "SELECT user_xid FROM post WHERE post_id = %s"
    cur.execute(query_owner, (post_id,))
    owner = cur.fetchone()

    if not owner or owner[0] != session['user'][0]:
        return "삭제 권한이 없습니다.", 403

    # 댓글 좋아요 삭제 (게시글의 모든 댓글에 대해)
    query_delete_comment_likes = """
        DELETE cl FROM comment_like cl
        JOIN comment c ON cl.comment_comment_id = c.comment_id
        WHERE c.post_id = %s
    """
    cur.execute(query_delete_comment_likes, (post_id,))

    # 댓글 삭제
    query_delete_comments = "DELETE FROM comment WHERE post_id = %s"
    cur.execute(query_delete_comments, (post_id,))

    # 게시글 좋아요 삭제
    query_delete_post_likes = "DELETE FROM post_like WHERE post_id = %s"
    cur.execute(query_delete_post_likes, (post_id,))

    # 게시글 삭제
    query_delete_post = "DELETE FROM post WHERE post_id = %s"
    cur.execute(query_delete_post, (post_id,))

    db.commit()

    return redirect(url_for('user_detail', user_xid=session['user'][0]))

#추가 - 댓글 삭제
@app.route('/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    if 'user' not in session:
        return redirect(url_for('login'))  # 로그인 여부 확인

    cur = db.cursor()

    # 댓글 소유자 확인
    query_owner = "SELECT user_xid FROM comment WHERE comment_id = %s"
    cur.execute(query_owner, (comment_id,))
    owner = cur.fetchone()

    if not owner or owner[0] != session['user'][0]:
        return "삭제 권한이 없습니다.", 403

    # 댓글 좋아요 삭제
    query_delete_likes = "DELETE FROM comment_like WHERE comment_comment_id = %s"
    cur.execute(query_delete_likes, (comment_id,))

    # 댓글 삭제
    query_delete_comment = "DELETE FROM comment WHERE comment_id = %s"
    cur.execute(query_delete_comment, (comment_id,))
    db.commit()

    return redirect(url_for('user_detail', user_xid=session['user'][0]))

#추가
@app.route('/post/new', methods=['GET', 'POST'])
def create_post():
    if 'user' not in session:
        return redirect(url_for('login'))  # 로그인 여부 확인

    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')

        # 데이터베이스에 게시글 저장
        query_insert_post = """
            INSERT INTO post (user_xid, title, content, created_at, updated_at, views)
            VALUES (%s, %s, %s, NOW(), NOW(), 0)
        """
        cur = db.cursor()
        cur.execute(query_insert_post, (session['user'][0], title, content))
        db.commit()

        return redirect(url_for('main'))  # 게시글 작성 후 메인 페이지로 이동

    return render_template('create_post.html')

#추가
@app.route('/post/<int:post_id>', methods=['GET'])
def post_detail(post_id):
    cur = db.cursor()

    query_update_views = "UPDATE post SET views = views + 1 WHERE post_id = %s"
    cur.execute(query_update_views, (post_id,))
    db.commit()

    # 게시글 정보 가져오기
    query_post = """
    SELECT p.title, p.content, p.created_at, p.views, u.nickname
    FROM post p
    JOIN user u ON p.user_xid = u.xid
    WHERE p.post_id = %s
    """
    cur.execute(query_post, (post_id,))
    post = cur.fetchone()

    if not post:
        return "게시글을 찾을 수 없습니다.", 404

    # 게시글 좋아요 수 가져오기
    query_likes = "SELECT COUNT(*) FROM post_like WHERE post_id = %s"
    cur.execute(query_likes, (post_id,))
    post_likes = cur.fetchone()[0]

    # 댓글 정보 가져오기
    query_comments = """
    SELECT c.comment_id, c.content, c.created_at, u.nickname
    FROM comment c
    JOIN user u ON c.user_xid = u.xid
    WHERE c.post_id = %s
    ORDER BY c.created_at ASC
    """
    cur.execute(query_comments, (post_id,))
    comments = cur.fetchall()
    

    # 댓글 좋아요 수 가져오기
    comment_likes = {}
    user_liked_comments = {}
    for comment in comments:
        cur.execute("SELECT COUNT(*) FROM comment_like WHERE comment_comment_id = %s", (comment[0],))
        comment_likes[comment[0]] = cur.fetchone()[0]
        cur.execute("SELECT 1 FROM comment_like WHERE comment_comment_id = %s AND user_xid = %s", (comment[0], session.get('user', [None])[0]))
        user_liked_comments[comment[0]] = cur.fetchone() is not None

    is_login = 'user' in session

    cur.execute("SELECT 1 FROM post_like WHERE post_id = %s AND user_xid = %s", (post_id, session.get('user', [None])[0]))
    user_liked_post = cur.fetchone() is not None

    return render_template(
        'post.html',
        post=post,
        comments=comments,
        post_likes=post_likes,
        comment_likes=comment_likes,
        is_login=is_login,
        post_id=post_id,
        user_liked_post=user_liked_post,
        user_liked_comments=user_liked_comments
    )

#추가
@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    if 'user' not in session:
        return redirect(url_for('login'))  # 로그인되지 않은 경우 로그인 페이지로 리다이렉트

    # 댓글 내용 가져오기
    content = request.form['content']
    user_xid = session['user'][0]  # 세션에서 사용자 ID 가져오기

    cur = db.cursor()
    # 댓글 삽입
    query_insert = """
    INSERT INTO comment (post_id, user_xid, content, created_at)
    VALUES (%s, %s, %s, NOW())
    """
    cur.execute(query_insert, (post_id, user_xid, content))
    db.commit()

    return redirect(url_for('post_detail', post_id=post_id))  # 댓글 작성 후 게시글 상세 페이지로 리다이렉트

#추가
@app.route('/ranking')
def ranking():
    cur = db.cursor()

    cur.execute("""
        SELECT u.nickname, COUNT(c.comment_id) AS comment_count
        FROM user u
        JOIN comment c ON u.xid = c.user_xid
        GROUP BY u.nickname
        ORDER BY comment_count DESC
        LIMIT 10
    """)
    comment_ranking = cur.fetchall()

    cur.execute("""
        SELECT u.nickname, COUNT(p.post_id) AS post_count
        FROM user u
        JOIN post p ON u.xid = p.user_xid
        GROUP BY u.nickname
        ORDER BY post_count DESC
        LIMIT 10
    """)
    post_ranking = cur.fetchall()

    cur.execute("""
        SELECT p.title, p.views
        FROM post p
        ORDER BY p.views DESC
        LIMIT 10
    """)
    view_ranking = cur.fetchall()

    cur.execute("""
        SELECT p.title, COUNT(pl.user_xid) AS like_count
        FROM post p
        JOIN post_like pl ON p.post_id = pl.post_id
        GROUP BY p.post_id, p.title
        ORDER BY like_count DESC
        LIMIT 10
    """)
    like_ranking = cur.fetchall()

    cur.execute("""
        SELECT 
        c.content AS comment_content, 
        COUNT(cl.comment_comment_id) AS like_count
        FROM comment c
        LEFT JOIN comment_like cl ON c.comment_id = cl.comment_comment_id
        GROUP BY c.comment_id
        ORDER BY like_count DESC
        LIMIT 10
    """)
    c_like_ranking = cur.fetchall()

    cur.close()

    return render_template(
        'ranking.html',
        comment_ranking=comment_ranking,
        post_ranking=post_ranking,
        view_ranking=view_ranking,
        like_ranking=like_ranking,
        c_like_ranking = c_like_ranking
    )




#-------------------------------------------------------------------------

#메인 페이지 라우터
@app.route('/', methods=['GET'])
def main():
    page = request.args.get('page', default=1, type=int)
    limit = 10
    user = session.get('user', None)
    user_xid = user[0] if user else None
    sort_by = request.args.get('sort_by', 'post_id')
    order = request.args.get('order', 'desc')
    maxpage = """
    SELECT COUNT(*) FROM post
    """
    cur = db.cursor()
    cur.execute(maxpage)
    maxpage = cur.fetchone()[0]
    cur.close()
    maxpage = maxpage//limit + 1
    
    if(page < 1):
        page = maxpage
    elif(page > maxpage):
        page = 1

    valid_columns = ['user_nickname', 'title', 'post_id', 'views']
    if sort_by not in valid_columns:
        sort_by = 'created_at'
    if order not in ['asc', 'desc']:
        order = 'desc'
    query = f"""
    SELECT  u.nickname as user_nickname, 
            p.title, 
            p.created_at, 
            IFNULL((SELECT COUNT(pl.post_id)
                    FROM post_like AS pl
                    WHERE p.post_id = pl.post_id
                    GROUP BY pl.post_id), 0) AS post_like, 
            p.views,
            {page},
            p.post_id,
            IF(EXISTS(SELECT 1 FROM post_like WHERE post_id = p.post_id AND user_xid = %s), 1, 0) AS liked
            , u.xid
    FROM post p
    JOIN user u ON p.user_xid = u.xid
    WHERE u.state = 'activate'
    ORDER BY {sort_by} {order}
    LIMIT {limit}
    OFFSET {page*limit - limit}
    """

    cs = db.cursor()
    cs.execute(query, (user_xid,))
    posts = cs.fetchall()
    cs.close()

    # 결과 반환
    return render_template('main.html'
                           , posts=posts
                           , is_login='user' in session
                           , userInfo=session.get('user', None)
                           , sort_by=sort_by
                           , order=order
                           , page=page)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5001)
