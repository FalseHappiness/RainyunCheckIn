import argparse
import os
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext

import requests
from PIL import Image, ImageTk
import io
import cv2
import numpy as np
from queue import Queue

from src.main import MainLogic
from src.ICR import main as icr_main, convert_matches_to_positions, find_part_positions

main_logic = MainLogic(None, {}, True)


def bytes_to_cv_image(img_bytes):
    """将bytes转换为OpenCV图像格式"""
    img_array = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)


# noinspection PyTypeChecker
def display_cv_image_in_frame(parent, cv_image, title):
    """在指定框架中显示OpenCV图像"""
    frame = ttk.LabelFrame(parent, text=title)
    frame.pack(side=tk.LEFT, padx=5, pady=5)

    # 调整图像大小
    height, width = cv_image.shape[:2]
    max_size = 40
    if width > max_size or height > max_size:
        scale = min(max_size / width, max_size / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        cv_image = cv2.resize(cv_image, (new_width, new_height))

    # 转换颜色空间 BGR to RGB
    cv_image_rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(cv_image_rgb)
    photo = ImageTk.PhotoImage(image)

    label = ttk.Label(frame, image=photo)
    label.image = photo  # 保持引用
    label.pack(padx=5, pady=5)


# noinspection PyTypeChecker
class CaptchaTesterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("验证码识别测试工具")
        self.root.geometry("1200x800")

        # 测试状态变量
        self.test_count = 0
        self.current_index = 0
        self.current_method = 'template'
        self.captcha_queue = Queue()
        self.is_running = False
        self.captcha_data_list = []

        # 变量
        self.sprite_label = None
        self.captcha_data_label = None
        self.log_text = None
        self.matches_scroll_frame = None
        self.matches_canvas = None
        self.bg_label = None
        self.status_label = None
        self.stats_label = None
        self.count_var = None
        self.method_var = None
        self.correct_button = None
        self.next_button = None
        self.prev_button = None
        self.stop_button = None
        self.start_button = None
        self.incorrect_button = None

        # 创建界面
        self.create_widgets()

    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 控制面板区域
        self.create_control_panel(main_frame)

        # 图像显示区域
        self.create_image_display(main_frame)

        # 日志区域
        self.create_log_area(main_frame)

        # 按钮区域
        self.create_button_area(main_frame)

    def create_control_panel(self, parent):
        control_frame = ttk.LabelFrame(parent, text="控制面板", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # 第一行：测试次数和匹配方法
        row1_frame = ttk.Frame(control_frame)
        row1_frame.pack(fill=tk.X, pady=5)

        # 测试次数设置
        ttk.Label(row1_frame, text="测试次数:").pack(side=tk.LEFT)
        self.count_var = tk.StringVar(value="100")
        count_entry = ttk.Entry(row1_frame, textvariable=self.count_var, width=10)
        count_entry.pack(side=tk.LEFT, padx=5)

        # 添加一些间距
        ttk.Label(row1_frame, width=5).pack(side=tk.LEFT)

        # 匹配方法设置（下拉选择框）
        ttk.Label(row1_frame, text="匹配方法:").pack(side=tk.LEFT)
        self.method_var = tk.StringVar(value="template")
        method_combobox = ttk.Combobox(
            row1_frame,
            textvariable=self.method_var,
            values=["template", "brute", "speed"],
            state="readonly",
            width=10
        )
        method_combobox.pack(side=tk.LEFT, padx=5)

        # 统计信息
        stats_frame = ttk.Frame(control_frame)
        stats_frame.pack(fill=tk.X, pady=5)

        self.stats_label = ttk.Label(stats_frame, text="正确率: 0/0 (0.00%)")
        self.stats_label.pack(side=tk.LEFT)

        self.status_label = ttk.Label(stats_frame, text="状态: 未开始")
        self.status_label.pack(side=tk.RIGHT)

        ttk.Label(stats_frame, width=5).pack(side=tk.RIGHT)

        self.captcha_data_label = ttk.Label(stats_frame, text="未选择测试图像")
        self.captcha_data_label.pack(side=tk.RIGHT)

    def create_image_display(self, parent):
        image_frame = ttk.LabelFrame(parent, text="验证码显示", padding=10)
        image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # 创建主容器框架（水平布局）
        main_container = ttk.Frame(image_frame)
        main_container.pack(fill=tk.BOTH, expand=True)

        # 主图像显示区域（左侧）
        main_image_frame = ttk.Frame(main_container)
        main_image_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 背景图显示
        bg_frame = ttk.LabelFrame(main_image_frame, text="背景图")
        bg_frame.pack(fill=tk.BOTH, expand=True, padx=(0, 5))

        self.bg_label = ttk.Label(bg_frame, text="无图像")
        self.bg_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 拼图显示
        sprite_frame = ttk.LabelFrame(main_image_frame, text="拼图")
        sprite_frame.pack(fill=tk.BOTH, expand=True, padx=(5, 0))

        self.sprite_label = ttk.Label(sprite_frame, text="无图像")
        self.sprite_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 匹配结果显示区域（右侧）
        matches_frame = ttk.LabelFrame(main_container, text="匹配结果比较")
        matches_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0))

        # 创建滚动框架用于匹配结果显示
        self.matches_canvas = tk.Canvas(matches_frame)
        scrollbar = ttk.Scrollbar(matches_frame, orient="vertical", command=self.matches_canvas.yview)
        self.matches_scroll_frame = ttk.Frame(self.matches_canvas)

        self.matches_scroll_frame.bind(
            "<Configure>",
            lambda e: self.matches_canvas.configure(scrollregion=self.matches_canvas.bbox("all"))
        )

        self.matches_canvas.create_window((0, 0), window=self.matches_scroll_frame, anchor="nw")
        self.matches_canvas.configure(yscrollcommand=scrollbar.set)

        self.matches_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_log_area(self, parent):
        log_frame = ttk.LabelFrame(parent, text="日志输出", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

    def create_button_area(self, parent):
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X)

        # 开始/停止按钮
        self.start_button = ttk.Button(button_frame, text="开始测试", command=self.start_test)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_button = ttk.Button(button_frame, text="停止测试", command=self.stop_test, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        # 导航按钮
        nav_frame = ttk.Frame(button_frame)
        nav_frame.pack(side=tk.LEFT, padx=20)

        self.prev_button = ttk.Button(nav_frame, text="上一个", command=self.previous_captcha, state=tk.DISABLED)
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))

        self.next_button = ttk.Button(nav_frame, text="下一个", command=self.next_captcha, state=tk.DISABLED)
        self.next_button.pack(side=tk.LEFT, padx=(0, 5))

        # 判断按钮
        judge_frame = ttk.Frame(button_frame)
        judge_frame.pack(side=tk.RIGHT)

        self.correct_button = ttk.Button(judge_frame, text="正确", command=lambda: self.judge_captcha(True),
                                         state=tk.DISABLED)
        self.correct_button.pack(side=tk.LEFT, padx=(0, 5))

        self.incorrect_button = ttk.Button(judge_frame, text="错误", command=lambda: self.judge_captcha(False),
                                           state=tk.DISABLED)
        self.incorrect_button.pack(side=tk.LEFT)

    def log_message(self, message):
        """添加日志消息"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_stats(self):
        """更新统计信息"""
        total = len(self.captcha_data_list)
        correct_count = sum(1 for item in self.captcha_data_list if item.get('correct') is True)
        if total > 0:
            accuracy = (correct_count / total) * 100
            self.stats_label.config(text=f"正确率: {correct_count}/{total} ({accuracy:.2f}%)")
        else:
            self.stats_label.config(text="正确率: 0/0 (0.00%)")

    def display_images(self, bg_img, sprite_img):
        """显示背景图和拼图"""
        try:
            # 显示背景图
            bg_image = Image.open(io.BytesIO(bg_img))
            bg_image.thumbnail((300, 200))
            bg_photo = ImageTk.PhotoImage(bg_image)
            self.bg_label.config(image=bg_photo)
            self.bg_label.image = bg_photo

            # 显示拼图
            sprite_image = Image.open(io.BytesIO(sprite_img))
            sprite_image.thumbnail((150, 200))
            sprite_photo = ImageTk.PhotoImage(sprite_image)
            self.sprite_label.config(image=sprite_photo)
            self.sprite_label.image = sprite_photo
        except Exception as e:
            self.log_message(f"显示图像错误: {e}")

    def display_match_comparisons(self, bg_img, sprite_img, matches):
        """在GUI中显示匹配结果比较"""
        # 清除之前的匹配结果显示
        for widget in self.matches_scroll_frame.winfo_children():
            widget.destroy()

        if not matches:
            no_match_label = ttk.Label(self.matches_scroll_frame, text="未找到匹配")
            no_match_label.pack(pady=10)
            return

        # 将bytes转换为OpenCV图像
        original_bg = bytes_to_cv_image(bg_img)
        original_sprite = bytes_to_cv_image(sprite_img)

        for i, match in enumerate(matches):
            match_frame = ttk.LabelFrame(self.matches_scroll_frame, text=f"匹配 {i + 1}")
            match_frame.pack(fill=tk.X, padx=5, pady=2)

            # Sprite原始区域
            sprite_x, sprite_y, sprite_w, sprite_h = match['sprite_rect']
            sprite_roi = original_sprite[sprite_y:sprite_y + sprite_h, sprite_x:sprite_x + sprite_w]

            # 旋转后的sprite
            rotated_sprite = match['rotated_sprite']
            if len(rotated_sprite.shape) == 2:  # 如果是灰度图，转换为BGR
                rotated_sprite_bgr = cv2.cvtColor(rotated_sprite, cv2.COLOR_GRAY2BGR)
            else:
                rotated_sprite_bgr = rotated_sprite

            # 匹配的背景区域
            bg_x, bg_y, bg_w, bg_h = match['bg_rect']
            bg_roi = original_bg[bg_y:bg_y + bg_h, bg_x:bg_x + bg_w]

            # 创建三列显示
            row_frame = ttk.Frame(match_frame)
            row_frame.pack(fill=tk.X, padx=5, pady=5)

            # 显示sprite区域
            display_cv_image_in_frame(row_frame, sprite_roi, f"Sprite {match['sprite_idx'] + 1}")

            # 显示旋转后的sprite
            display_cv_image_in_frame(row_frame, rotated_sprite_bgr, f"旋转 {match['angle']}°")

            # 显示匹配的背景区域
            display_cv_image_in_frame(row_frame, bg_roi, f"相似度: {match['similarity']:.1f}%")

    def get_captcha_data(self):
        """获取验证码数据"""
        try:
            data = main_logic.get_captcha_data()
            bg_img, sprite_img = main_logic.get_captcha_images(data)
            return bg_img, sprite_img, data
        except Exception as e:
            self.log_message(f"获取验证码失败: {e}")
            return None, None, None

    def captcha_worker(self):
        """后台获取验证码的工作线程"""
        while self.is_running and len(self.captcha_data_list) < self.test_count:
            try:
                bg_img, sprite_img, data = self.get_captcha_data()
                if bg_img and sprite_img:
                    # 识别验证码
                    matches = icr_main(bg_img, sprite_img, self.current_method)

                    captcha_data = {
                        'bg_img': bg_img,
                        'sprite_img': sprite_img,
                        'data': data,
                        'matches': matches,
                        'correct': None
                    }

                    self.captcha_data_list.append(captcha_data)

                    # 更新GUI
                    self.root.after(0, self.on_new_captcha)

                    self.log_message(f"已获取验证码 {len(self.captcha_data_list)}/{self.test_count}")

                # 避免请求过于频繁
                time.sleep(0.5)

            except Exception as e:
                self.log_message(f"获取验证码时出错: {e}")
                time.sleep(1)

        self.root.after(0, self.on_captcha_complete)

    def on_new_captcha(self):
        """当有新验证码时的回调"""
        self.update_stats()

        # 如果是第一个验证码，自动显示
        if len(self.captcha_data_list) == 1:
            self.current_index = 0
            self.show_current_captcha()

        # 启用导航按钮
        if len(self.captcha_data_list) > 0:
            self.prev_button.config(state=tk.NORMAL)
            self.next_button.config(state=tk.NORMAL)
            self.correct_button.config(state=tk.NORMAL)
            self.incorrect_button.config(state=tk.NORMAL)

    def on_captcha_complete(self):
        """验证码获取完成时的回调"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 获取完成")
        self.log_message("验证码获取完成")

    def show_current_captcha(self):
        """显示当前索引的验证码"""
        if 0 <= self.current_index < len(self.captcha_data_list):
            captcha_data = self.captcha_data_list[self.current_index]

            # 显示图像
            self.display_images(captcha_data['bg_img'], captcha_data['sprite_img'])

            # 显示匹配结果
            self.display_match_comparisons(
                captcha_data['bg_img'],
                captcha_data['sprite_img'],
                captcha_data['matches']
            )

            correct = captcha_data.get('correct', None)

            # 显示识别结果
            positions = convert_matches_to_positions(captcha_data['matches'])
            self.captcha_data_label.config(
                text=f"测试图像 {self.current_index + 1}: {'未记' if correct is None else ('正确' if correct else '错误')}")
            self.log_message(
                f"当前验证码 {self.current_index + 1}: {'' if correct is None else ('当前判断为：' + ('正确' if correct else '错误') + '，')}识别位置 {positions}")

    def start_test(self):
        """开始测试"""
        try:
            self.test_count = int(self.count_var.get())
        except ValueError:
            self.log_message("错误: 请输入有效的测试次数")
            return

        # 重置状态
        self.current_index = 0
        self.captcha_data_list = []

        # 更新UI状态
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="状态: 运行中")

        # 清空日志
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

        self.current_method = self.method_var.get()

        self.log_message(f"开始测试，使用匹配方法 {self.current_method}，计划获取 {self.test_count} 个验证码")

        # 启动后台线程获取验证码
        thread = threading.Thread(target=self.captcha_worker, daemon=True)
        thread.start()

    def stop_test(self):
        """停止测试"""
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.status_label.config(text="状态: 已停止")
        self.log_message("测试已停止")

    def previous_captcha(self):
        """显示上一个验证码"""
        if self.current_index > 0:
            self.current_index -= 1
            self.show_current_captcha()

    def next_captcha(self):
        """显示下一个验证码"""
        if self.current_index < len(self.captcha_data_list) - 1:
            self.current_index += 1
            self.show_current_captcha()

    def judge_captcha(self, is_correct):
        """判断当前验证码是否正确"""
        if 0 <= self.current_index < len(self.captcha_data_list):
            captcha_data = self.captcha_data_list[self.current_index]

            if is_correct:
                self.log_message(f"验证码 {self.current_index + 1}: 标记为正确")
            else:
                self.log_message(f"验证码 {self.current_index + 1}: 标记为错误")
                self.save_failed_captcha(captcha_data, self.current_index + 1)

            captcha_data['correct'] = is_correct
            self.update_stats()

            # 自动切换到下一个
            if self.current_index < len(self.captcha_data_list) - 1:
                self.current_index += 1
                self.show_current_captcha()

    def save_failed_captcha(self, captcha_data, index):
        """保存失败的验证码"""
        try:
            timestamp = str(int(time.time()))
            fail_folder = os.path.join("fails", f"{timestamp}_{index}")
            os.makedirs(fail_folder, exist_ok=True)

            with open(os.path.join(fail_folder, "bg.jpg"), "wb") as f:
                f.write(captcha_data['bg_img'])
            with open(os.path.join(fail_folder, "sprite.jpg"), "wb") as f:
                f.write(captcha_data['sprite_img'])

            self.log_message(f"失败案例已保存到: {fail_folder}")
        except Exception as e:
            self.log_message(f"保存失败案例时出错: {e}")


def main():
    root = tk.Tk()
    CaptchaTesterGUI(root)
    root.mainloop()


def auto_test(test_count, method):
    correct_count = 0
    """运行测试"""
    for i in range(1, test_count + 1):
        print(f"\n=== 测试 {i}/{test_count} ===")

        bg_img, sprite_img, data = (None, None, None)
        # 获取验证码
        # noinspection PyBroadException
        try:
            data = main_logic.get_captcha_data()
            bg_img, sprite_img = main_logic.get_captcha_images(data)
        except:
            pass

        if bg_img is None or sprite_img is None:
            print("获取验证码失败，跳过本次测试")
            continue

        # 识别验证码
        try:
            # 直接传入二进制数据
            positions = find_part_positions(bg_img, sprite_img, method)
            print("识别结果:", positions)

            is_correct = False

            try:
                form_data = main_logic.build_verify_form(data, positions)

                response = requests.post(
                    'https://turing.captcha.qcloud.com/cap_union_new_verify',
                    data=form_data,
                    headers=main_logic.common_headers
                )
                response.raise_for_status()  # 检查请求是否成功

                result = response.json()

                if int(result['errorCode']) == 0:
                    is_correct = True

                print(result)
            except Exception as e:
                print('自动验证错误', e)

            # 验证
            if is_correct:
                correct_count += 1
                print("√ 正确")
            else:
                fail_folder = os.path.join("fails", f"{int(time.time())}_{i}")
                os.makedirs(fail_folder, exist_ok=True)

                with open(os.path.join(fail_folder, "bg.jpg"), "wb") as f:
                    f.write(bg_img)
                with open(os.path.join(fail_folder, "sprite.jpg"), "wb") as f:
                    f.write(sprite_img)

                print("× 错误")

        except Exception as e:
            print(f"识别过程中出错: {e}")
            continue

        # 避免请求过于频繁
        # time.sleep(5)

    # 计算并显示准确率
    accuracy = (correct_count / test_count) * 100
    print(f"\n测试完成，正确率: {accuracy:.2f}% ({correct_count}/{test_count})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='验证码识别准确率测试')
    parser.add_argument('--count', type=int, default=100, help='测试次数，默认为100')
    parser.add_argument('--auto', action='store_true', help='自动模式（会出现请求过于频繁）')
    parser.add_argument('--method', type=str, default='template', help='匹配方法，默认为 template')

    args = parser.parse_args()

    if args.auto:
        auto_test(args.count, args.method)
    else:
        main()
