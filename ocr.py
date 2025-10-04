import cv2
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Union, BinaryIO


def load_and_preprocess(image_data: Union[str, Path, bytes, BinaryIO], threshold: int = 30) -> np.ndarray:
    """
    加载图像并预处理，提取接近黑色的部分（基于BGR色彩空间）

    参数:
        image_data: 可以是文件路径(字符串或Path对象)、二进制数据(bytes)或文件类对象
        threshold: 黑色阈值，所有BGR通道都低于此值被视为黑色

    返回:
        处理后的二值化掩码图像
    """
    # 处理路径输入
    if isinstance(image_data, (str, Path)):
        img = cv2.imread(str(image_data))
    # 处理二进制数据
    elif isinstance(image_data, bytes):
        img = cv2.imdecode(np.frombuffer(image_data, np.uint8), cv2.IMREAD_COLOR)
    # 处理文件类对象(如上传的文件)
    elif hasattr(image_data, 'read'):
        img = cv2.imdecode(np.frombuffer(image_data.read(), np.uint8), cv2.IMREAD_COLOR)
    else:
        raise ValueError("不支持的输入类型，请提供文件路径、二进制数据或文件类对象")

    if img is None:
        raise ValueError("图像加载失败，请检查输入数据是否正确")

    # 创建一个掩码，其中所有BGR通道都低于阈值
    mask = cv2.inRange(img, (0, 0, 0), (threshold, threshold, threshold))
    return mask


def extract_blackest_parts(sprite_mask, num_parts=3):
    """将sprite均匀分成三部分，提取每部分最黑的区域"""
    height, width = sprite_mask.shape
    part_width = width // num_parts

    parts = []
    for i in range(num_parts):
        part = sprite_mask[:, i * part_width:(i + 1) * part_width]
        parts.append(part)

    return parts


def find_part_positions(bg_mask, sprite_parts, scale_range=(1.45, 1.55), angle_range=(-75, 75), step=5):
    """在图像中查找所有sprite部分的位置，考虑旋转和缩放"""
    all_positions = []
    working_mask = bg_mask.copy()  # 创建一个工作副本，用于屏蔽已匹配区域

    for part in sprite_parts:
        result = find_single_part_positions(working_mask, part, scale_range, angle_range, step)

        if result:
            x, y, scale = result
            # 获取匹配部分的尺寸
            resized_part = cv2.resize(part, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
            h, w = resized_part.shape

            # 屏蔽已匹配区域（在周围扩大一些范围）
            margin = 10  # 扩大一些边缘
            cv2.rectangle(working_mask,
                          (max(0, x - w // 2 - margin), max(0, y - h // 2 - margin)),
                          (min(working_mask.shape[1], x + w // 2 + margin),
                           min(working_mask.shape[0], y + h // 2 + margin)),
                          0, -1)  # 填充黑色

            all_positions.append((x, y))  # 只存储坐标
        else:
            all_positions.append(None)

    return all_positions


def find_single_part_positions(bg_mask, sprite_part, scale_range, angle_range, step):
    """在图像中查找单个sprite部分的位置"""
    best_matches = []
    bg_height, bg_width = bg_mask.shape
    part_height, part_width = sprite_part.shape

    # 尝试不同的缩放比例
    for scale in np.linspace(scale_range[0], scale_range[1], num=int((scale_range[1] - scale_range[0]) / 0.1) + 1):
        resized_part = cv2.resize(sprite_part, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        resized_height, resized_width = resized_part.shape

        # 如果缩放后的部分比图像还大，跳过
        if resized_height > bg_height or resized_width > bg_width:
            continue

        # 尝试不同的旋转角度
        for angle in range(angle_range[0], angle_range[1] + 1, step):
            # 旋转sprite部分
            M = cv2.getRotationMatrix2D((resized_width / 2, resized_height / 2), angle, 1)
            rotated_part = cv2.warpAffine(resized_part, M, (resized_width, resized_height))

            # 执行模板匹配
            result = cv2.matchTemplate(bg_mask, rotated_part, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)

            # 记录匹配结果
            best_matches.append((max_val, max_loc, scale, angle, resized_width, resized_height))

    # 按匹配质量排序，取最佳匹配
    if best_matches:
        best_matches.sort(reverse=True, key=lambda x: x[0])
        best_match = best_matches[0]
        x, y = best_match[1]
        # 返回中心点坐标和缩放比例
        return (x + best_match[4] // 2, y + best_match[5] // 2, best_match[2])
    else:
        return None


def display_results(bg_path, all_positions):
    """显示结果 - 只显示点和序号"""
    img = cv2.imread(str(bg_path))
    plt.figure(figsize=(12, 6))

    # 显示原始图像
    plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.title('Detected Positions')

    # 标记点
    colors = ['red', 'blue', 'green']  # 不同部分用不同颜色标记
    markers = ['o', 's', '^']  # 不同形状的标记

    for i, pos in enumerate(all_positions):
        if pos is not None:
            x, y = pos
            plt.scatter(x, y, c=colors[i % len(colors)], marker=markers[i % len(markers)], s=100)
            plt.text(x, y, f"{i + 1}", color='white', ha='center', va='center', fontsize=12,
                     bbox=dict(facecolor=colors[i % len(colors)], alpha=0.7, boxstyle='round'))

    plt.tight_layout()
    plt.show()


def main(bg_path, sprite_path, show_results=False, show_preprocessed=False):
    # 加载并预处理图像
    bg_mask = load_and_preprocess(bg_path)
    sprite_mask = load_and_preprocess(sprite_path)

    # 如果需要显示预处理结果
    if show_preprocessed:
        plt.figure(figsize=(12, 6))

        # 显示预处理后的背景
        plt.subplot(1, 2, 1)
        plt.imshow(cv2.cvtColor(bg_mask, cv2.COLOR_BGR2RGB))
        plt.title('Preprocessed Background')

        # 显示预处理后的sprite
        plt.subplot(1, 2, 2)
        plt.imshow(cv2.cvtColor(sprite_mask, cv2.COLOR_BGR2RGB))
        plt.title('Preprocessed Sprite')

        plt.tight_layout()
        plt.show()

    # 分割sprite并获取每个部分
    sprite_parts = extract_blackest_parts(sprite_mask)

    # 在图像中查找所有sprite部分的位置
    all_positions = find_part_positions(bg_mask, sprite_parts)

    if show_results:
        # 显示结果
        display_results(bg_path, all_positions)

    return all_positions


if __name__ == "__main__":
    # 使用示例图片路径
    bg_path = "tests/bg.jpg"
    sprite_path = "tests/sprite.jpg"

    # 检查文件是否存在
    if not Path(bg_path).exists() or not Path(sprite_path).exists():
        print("测试图片不存在，请确保tests/bg.jpg和tests/sprite.jpg存在")
    else:
        positions = main(bg_path, sprite_path, True, True)
        print("找到的位置坐标:")
        for i, pos in enumerate(positions):
            print(f"部分 {i + 1}: {pos}")
