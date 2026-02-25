# 家庭财务管理系统

一个简洁、温暖的家庭财务管理工具。

## 功能

- 记录收入和支出
- 按分类管理交易
- 月度收支统计
- 简洁优雅的界面

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行应用

```bash
python src/main.py
```

### 3. 访问应用

打开浏览器访问: http://localhost:5001

## 技术栈

- Flask 3.0.0
- SQLAlchemy 2.x
- SQLite 3

## 项目结构

```
0225-FamilyFin/
├── src/                    # 源代码
│   ├── main.py            # 应用入口
│   ├── models.py          # 数据模型
│   ├── database.py        # 数据库配置
│   └── config.py          # 配置文件
├── data/                  # 数据库文件
├── docs/                  # 设计文档
└── preview.html           # 静态预览
```

## 开发

### 初始化数据库

应用首次运行时会自动初始化数据库和预设分类。

手动初始化可访问: http://localhost:5001/init-db

### 预设分类

**收入：** 工资、奖金
**支出：** 餐饮、交通

## 许可

MIT License
