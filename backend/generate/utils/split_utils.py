import re


def split_and_lowercase(model_name):
    # 查找所有大写字母开头的单词（包括首字母）
    matches = re.findall(r'[A-Z][a-z]*', model_name)
    # 转换为小写
    return [match.lower() for match in matches if match.lower() != 'model']


def convert_model_to_path(model_name):
    # 1. 查找所有大写字母开头的单词
    matches = re.findall(r'[A-Z][a-z]*', model_name)
    
    # 2. 转换为小写并过滤掉末尾的"model"
    words = [match.lower() for match in matches if match.lower() != 'model']

    # 3. 拼接路径
    return '/'.join(words), '.'.join(words)




if __name__ == "__main__":
    # 示例
    model_names = [
        "ConfigSmsSignModel",
        "UserLoginInfoModel",
        "HTTPRequestHandlerModel",
        "XMLParserModel",
        "PDFDocumentReaderModel",
        "UserModel",  # 特殊情况：只有一个有效单词
    ]

    for model_name in model_names:
        result = convert_model_to_path(model_name)
        print(f"{model_name} -> {result}")