import re


def replace_dash_with_tilde(text):
    """
    将字符串中所有"数字-数字"格式的连字符(-)替换为波浪号(~)

    参数:
    text (str): 输入的字符串

    返回:
    str: 替换后的字符串
    """
    # 正则表达式模式：匹配"数字-数字"格式
    pattern = r'\d+-\d+'

    # 使用re.sub()函数进行替换
    # 第一个参数是匹配模式
    # 第二个参数是替换函数，将匹配到的内容中的-替换为~
    # 第三个参数是输入字符串
    return re.sub(pattern, lambda x: x.group().replace('-', '~'), text)


# 测试示例
if __name__ == "__main__":
    # 测试字符串，包含多个"数字-数字"格式
    test_strings = [
        "今天的日期是2023-06-27",
        "这个范围是1-100，另一个是500-1000",
        "产品编号是A123-456-B789",
        "价格区间：100-200元，200-300元",
        "无匹配项：hello-world 123 456"
    ]

    print("替换前\t\t\t\t替换后")
    print("-" * 80)

    for s in test_strings:
        # 格式化输出，使替换前后的字符串对齐
        print(f"{s[:30]:<35}\t\t{replace_dash_with_tilde(s)[:30]:<35}")
