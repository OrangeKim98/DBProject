FLASK 초기 세팅

1. 프로젝트 파일 생성  -> 생성 후 생성 파일로 이동 cd {PrijectFile}
2. python -m venv {name}  # 가상환경 생성
3. venv\Scripts\activate   # 가상환경 접속
5. pip install -r requirements.txt

가상환경에 pip list 입력 후 아래와 같이 나온다면 성공

Package      Version
------------ -------
blinker      1.8.2
cffi         1.17.1
click        8.1.7
colorama     0.4.6
cryptography 43.0.3
Flask        3.0.3
itsdangerous 2.2.0
Jinja2       3.1.4
MarkupSafe   3.0.2
pip          24.2
pycparser    2.22
PyMySQL      1.1.1
Werkzeug     3.1.2