import os

import matplotlib.pyplot as plt
import requests
from playwright.sync_api import sync_playwright, Position

import main
import ocr
import time


# noinspection PyMethodMayBeStatic
class CaptchaTester:
    def __init__(self, test_count=100, auto_check=False, batch_manual=False):
        self.test_count = test_count
        self.auto_check = auto_check
        self.batch_manual = batch_manual  # 新增：批量手动模式
        self.correct_count = 0
        self.base_url = "https://turing.captcha.qcloud.com"
        self.test_results = []  # 存储测试结果

    def get_captcha_data(self):
        """获取验证码图片和sprite图片"""
        try:
            data = main.get_captcha_data()
            bg_img, sprite_img = main.get_captcha_images(data)
            return bg_img, sprite_img, data
        except Exception as e:
            raise Exception(f"获取验证码失败: {e}")

    def display_captcha(self, bg_img: bytes, sprite_img: bytes, positions):
        """Display captcha images with detection results"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 10))

        # Display sprite image
        sprite_array = np.frombuffer(sprite_img, np.uint8)
        sprite_cv = cv2.imdecode(sprite_array, cv2.IMREAD_COLOR)
        ax1.imshow(cv2.cvtColor(sprite_cv, cv2.COLOR_BGR2RGB))
        ax1.set_title("Sprite Image")
        ax1.axis('off')

        # Display marked background
        bg_array = np.frombuffer(bg_img, np.uint8)
        bg_cv = cv2.imdecode(bg_array, cv2.IMREAD_COLOR)
        ax2.imshow(cv2.cvtColor(bg_cv, cv2.COLOR_BGR2RGB))

        # Mark detection points
        colors = ['red', 'blue', 'green']
        markers = ['o', 's', '^']
        for i, pos in enumerate(positions):
            if pos:
                ax2.scatter(pos[0], pos[1], c=colors[i], marker=markers[i], s=100)
                ax2.text(pos[0], pos[1], str(i + 1), color='white', ha='center', va='center',
                         fontsize=12, bbox=dict(facecolor=colors[i], alpha=0.7, boxstyle='round'))

        ax2.set_title("Detection Result")
        ax2.axis('off')
        plt.tight_layout()
        plt.show()

    def ask_user_verification(self, test_index=None) -> bool:
        """询问用户识别是否正确"""
        if test_index is not None:
            prompt = f"测试 {test_index}/{self.test_count} - 识别是否正确? (y/n): "
        else:
            prompt = "识别是否正确? (y/n): "

        while True:
            answer = input(prompt).strip().lower()
            if answer in ['y', 'yes']:
                return True
            elif answer in ['n', 'no']:
                return False
            else:
                print("请输入 y/n 或 yes/no")

    def batch_ask_user_verification(self):
        """批量询问用户识别结果"""
        print(f"\n=== 批量验证模式 ===")
        print(f"共 {len(self.test_results)} 个测试结果需要验证")

        for i, result in enumerate(self.test_results):
            bg_img, sprite_img, positions, test_index = result

            # 显示验证码和识别结果
            self.display_captcha(bg_img, sprite_img, positions)

            # 询问用户是否正确
            is_correct = self.ask_user_verification(test_index)

            if is_correct:
                self.correct_count += 1
                print(f"测试 {test_index}: √ 正确")
            else:
                # 保存错误案例
                timestamp = str(int(time.time()))
                fail_folder = os.path.join("fails", f"{timestamp}_{test_index}")
                os.makedirs(fail_folder, exist_ok=True)

                with open(os.path.join(fail_folder, "bg.jpg"), "wb") as f:
                    f.write(bg_img)
                with open(os.path.join(fail_folder, "sprite.jpg"), "wb") as f:
                    f.write(sprite_img)

                print(f"测试 {test_index}: × 错误")

    def run_test(self):
        """运行测试"""
        if self.batch_manual and not self.auto_check:
            # 批量手动模式：先获取所有图片，再统一验证
            print("批量手动模式：先获取所有验证码图片...")

            for i in range(1, self.test_count + 1):
                print(f"\n获取验证码 {i}/{self.test_count}")

                # 获取验证码
                try:
                    bg_img, sprite_img, data = self.get_captcha_data()
                    if bg_img is None or sprite_img is None:
                        print("获取验证码失败，跳过本次测试")
                        continue

                    # 识别验证码
                    positions = ocr.main(bg_img, sprite_img, False, False)
                    print(f"识别结果 {i}:", positions)

                    # 存储结果，稍后验证
                    self.test_results.append((bg_img, sprite_img, positions, i))

                    # 避免请求过于频繁
                    time.sleep(1)

                except Exception as e:
                    print(f"获取或识别验证码 {i} 时出错: {e}")
                    continue

            # 批量验证所有结果
            self.batch_ask_user_verification()

        else:
            # 原始模式：逐个获取和验证
            for i in range(1, self.test_count + 1):
                print(f"\n=== 测试 {i}/{self.test_count} ===")

                is_correct = False

                bg_img, sprite_img = None, None

                if self.auto_check:
                    try:
                        with sync_playwright() as p:
                            browser = p.webkit.launch(headless=True)

                            page = browser.new_page()

                            with open(
                                    os.path.join(os.path.dirname(os.path.abspath(__file__)), "captcha.html"),
                                    'r', encoding='utf-8'
                            ) as file:
                                html_content = file.read()

                            page.set_content(html_content)

                            page.wait_for_load_state("networkidle")

                            page.wait_for_selector("iframe")

                            iframe = page.query_selector("iframe").content_frame()

                            sprite_url = iframe.eval_on_selector(
                                ".tc-instruction-icon img",
                                "img => img.src"
                            )
                            bg_url = sprite_url.replace('img_index=0', 'img_index=1')

                            bg_img, sprite_img = (
                                requests.get(bg_url).content,
                                requests.get(sprite_url).content
                            )

                            bg_scalc_rate = 340 / 672

                            for _, coord in enumerate(
                                    ocr.find_part_positions(
                                        ocr.load_and_preprocess(bg_img),
                                        ocr.extract_blackest_parts(ocr.load_and_preprocess(sprite_img))
                                    ), start=1
                            ):
                                if len(coord) == 2:
                                    x, y = coord
                                    iframe.click(
                                        "#tcOperation",
                                        position=Position({'x': x * bg_scalc_rate, 'y': y * bg_scalc_rate})
                                    )
                                    time.sleep(0.1)

                            with page.expect_response(
                                    lambda res: "https://turing.captcha.qcloud.com/cap_union_new_verify" in res.url
                            ) as response_info:
                                iframe.click(".tc-action.verify-btn")
                                response = response_info.value

                            if response.ok:
                                result = response.json()
                                if result.get('randstr', None) and result.get('ticket', None):
                                    is_correct = True

                            browser.close()
                    except Exception as e:
                        print(f"Playwright 完成验证码失败: {e}")
                        continue
                else:
                    # 获取验证码
                    try:
                        bg_img, sprite_img, data = self.get_captcha_data()
                        if bg_img is None or sprite_img is None:
                            print("获取验证码失败，跳过本次测试")
                            continue
                    except Exception as e:
                        print(f"获取验证码失败: {e}")
                        continue

                    # 识别验证码
                    try:
                        # 直接传入二进制数据
                        positions = ocr.main(bg_img, sprite_img, False, False)
                        print("识别结果:", positions)

                        # 显示结果
                        self.display_captcha(bg_img, sprite_img, positions)

                        is_correct = self.ask_user_verification(i)

                    except Exception as e:
                        print(f"识别过程中出错: {e}")
                        continue

                # 验证
                if is_correct:
                    self.correct_count += 1
                    print("√ 正确")
                else:
                    # 获取当前时间戳
                    timestamp = str(int(time.time()))

                    fail_folder = os.path.join("fails", timestamp)

                    # 确保目录存在
                    os.makedirs(fail_folder, exist_ok=True)

                    if bg_img:
                        # 将 bytes 写入文件
                        with open(os.path.join(fail_folder, f"bg.jpg"), "wb") as f:
                            f.write(bg_img)
                    if sprite_img:
                        with open(os.path.join(fail_folder, f"sprite.jpg"), "wb") as f:
                            f.write(sprite_img)

                    print("× 错误")

                # 避免请求过于频繁
                # if self.auto_check:
                #     time.sleep(5)

        # 计算并显示准确率
        accuracy = (self.correct_count / self.test_count) * 100
        print(f"\n测试完成，正确率: {accuracy:.2f}% ({self.correct_count}/{self.test_count})")


if __name__ == "__main__":
    import argparse
    import cv2
    import numpy as np

    parser = argparse.ArgumentParser(description='验证码识别准确率测试')
    parser.add_argument('--count', type=int, default=100, help='测试次数，默认为100')
    parser.add_argument('--auto', action='store_true', help='自动判断正误（有问题）')
    parser.add_argument('--batch', action='store_true', help='批量手动模式（auto关闭时有效）')

    args = parser.parse_args()

    tester = CaptchaTester(test_count=args.count, auto_check=args.auto, batch_manual=args.batch)
    tester.run_test()
