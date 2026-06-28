"""
校园智能失物招领系统 - 桌面应用启动器
打包为独立可执行程序，双击即可运行
采用进程内启动Flask，自动打开浏览器，无需tkinter
"""
import os
import sys
import threading
import time
import webbrowser
import socket


# ========== 路径解析 ==========
def get_resource_dir():
    """获取资源文件目录"""
    if getattr(sys, 'frozen', False):
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass and os.path.isdir(os.path.join(meipass, 'frontend')):
            return meipass
        internal = os.path.join(os.path.dirname(sys.executable), '_internal')
        if os.path.isdir(os.path.join(internal, 'frontend')):
            return internal
        return os.path.dirname(sys.executable)
    # 开发环境: 当前py文件所在目录（code/）
    return os.path.dirname(os.path.abspath(__file__))


def get_app_root():
    """获取应用根目录"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # 开发环境: code/的父目录（项目根目录）
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def start_server():
    """启动Flask服务并自动打开浏览器"""
    app_root = get_app_root()

    host = '127.0.0.1'
    port = 8080

    # 检查端口是否已占用
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            # 服务已在运行，直接打开浏览器
            sock.close()
            webbrowser.open(f'http://{host}:{port}')
            return
    except Exception:
        pass
    finally:
        sock.close()

    # 在线程中启动Flask
    def run_flask():
        from api import app
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # 等待服务就绪
    for i in range(30):
        time.sleep(1)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                sock.close()
                # 自动打开浏览器
                webbrowser.open(f'http://{host}:{port}')
                return
        except Exception:
            pass
        finally:
            sock.close()


if __name__ == '__main__':
    start_server()
    # 保持进程运行（daemon线程随主进程退出）
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
