import os

import matplotlib.pyplot as plt
import requests

import main
from ocr import main as ocr_main
import time


class CaptchaTester:
    def __init__(self, test_count=100, auto_check=False):
        self.test_count = test_count
        self.auto_check = auto_check
        self.correct_count = 0
        self.base_url = "https://turing.captcha.qcloud.com"

    def get_captcha_data(self):
        """获取验证码图片和sprite图片"""
        try:
            data = main.get_captcha_data()
            bg_img, sprite_img = main.get_captcha_images(data)
            return bg_img, sprite_img, data
        except Exception as e:
            raise f"获取验证码失败: {e}"

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

    def ask_user_verification(self) -> bool:
        """询问用户识别是否正确"""
        while True:
            answer = input("识别是否正确? (y/n): ").strip().lower()
            if answer in ['y', 'yes']:
                return True
            elif answer in ['n', 'no']:
                return False
            else:
                print("请输入 y/n 或 yes/no")

    def run_test(self):
        """运行测试"""
        for i in range(1, self.test_count + 1):
            print(f"\n=== 测试 {i}/{self.test_count} ===")

            # 获取验证码
            bg_img, sprite_img, data = self.get_captcha_data()
            if bg_img is None or sprite_img is None:
                print("获取验证码失败，跳过本次测试")
                continue

            # 识别验证码
            try:
                # 直接传入二进制数据
                positions = ocr_main(bg_img, sprite_img)
                print("识别结果:", positions)

                is_correct = False

                # 显示结果
                self.display_captcha(bg_img, sprite_img, positions)

                if self.auto_check:
                    try:
                        form_data = main.build_verify_form(data, positions)

                        response = requests.post(
                            self.base_url + '/cap_union_new_verify',
                            data=form_data,
                            headers=main.COMMON_HEADERS
                        )
                        response.raise_for_status()  # 检查请求是否成功

                        result = response.json()

                        if int(result['errorCode']) == 0:
                            is_correct = True
                    except Exception as e:
                        print('自动验证错误', e)
                else:
                    is_correct = self.ask_user_verification()

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

                    # 将 bytes 写入文件
                    with open(os.path.join(fail_folder, f"bg.jpg"), "wb") as f:
                        f.write(bg_img)
                    with open(os.path.join(fail_folder, f"sprite.jpg"), "wb") as f:
                        f.write(sprite_img)

                    print("× 错误")

            except Exception as e:
                print(f"识别过程中出错: {e}")
                continue

            # 避免请求过于频繁
            if self.auto_check:
                time.sleep(5)

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

    args = parser.parse_args()

    tester = CaptchaTester(test_count=args.count, auto_check=args.auto)
    tester.run_test()
