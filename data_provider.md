# `data_provider.py` 使用说明文档

## 1. 模块概述

`data_provider.py` 模块旨在将**数据获取**的逻辑与**数据分析**的逻辑完全分离。它通过定义一个标准化的数据提供者接口，使得主分析程序 `analyze_performance.py` 无需关心数据具体来自哪里（Wind、数据库、本地文件等），从而实现了高度的模块化和可扩展性。

## 2. 设计模式

本模块采用的是经典的**策略设计模式 (Strategy Pattern)**。

#### 2.1. `DataProvider` (抽象基类)

这是一个“契约”或“接口”类。它规定了任何一个数据提供者都**必须**拥有一个名为 `get_data` 的方法。这确保了无论我们未来接入何种数据源，它们都能被主程序以相同的方式调用。

#### 2.2. `WindDataProvider` (具体实现类)

这是 `DataProvider` 接口的一个具体实现。它专门负责处理与 Wind API (`WindPy`) 的所有交互，包括：
- 自动连接 (`w.start()`)
- 调用 `w.wsd` 获取数据
- 处理API错误
- 在对象被销毁时自动断开连接 (`w.stop()`)

## 3. 如何使用 `WindDataProvider`

在任何需要获取Wind数据的脚本中，您可以像下面这样使用它：

```python
# 1. 导入 WindDataProvider 类
from data_provider import WindDataProvider
import logging

# (确保已配置好logging)

# 2. 初始化数据提供者
# 在初始化时，它会自动检查并连接到Wind终端
wind_provider = WindDataProvider()

# 3. 定义要获取的资产代码和时间范围
codes_to_fetch = ['000300.SH', '000905.SH'] # 沪深300, 中证500
start = '2024-01-01'
end = '2024-01-31'

# 4. 调用 get_data 方法获取数据
# 返回的是一个标准的、以日期为索引的 pandas DataFrame
financial_data = wind_provider.get_data(codes_to_fetch, start, end)

if financial_data is not None:
    logging.info("成功获取数据:")
    logging.info(financial_data.head())

# 5. 结束使用
# 当 wind_provider 对象生命周期结束时 (例如程序退出)，
# 它会自动调用 w.stop() 来断开与Wind的连接，无需手动管理。
```

## 4. 如何扩展（设计该模块的初衷）

这个设计的最大好处在于，如果未来您不想再使用Wind，而是想从本地的CSV文件读取数据，您**完全不需要修改主程序 `analyze_performance.py`**。

您只需在 `data_provider.py` 中新增一个数据提供者即可。

#### 扩展样例：创建一个 `CsvDataProvider`

假设您有一些CSV文件，每个文件包含一个资产的时间序列数据。您可以像这样创建一个新的提供者：

```python
# 在 data_provider.py 中新增以下代码

import pandas as pd
from data_provider import DataProvider # 导入基类

class CsvDataProvider(DataProvider):
    """一个从本地CSV文件读取数据的数据提供者"""
    def get_data(self, codes, start_date, end_date):
        # 在这个简化样例中，我们假设code就是文件名的一部分
        # 例如 code '000300.SH' 对应文件 '000300.SH.csv'
        try:
            # 假设我们只读取第一个code的数据
            file_path = f"{codes[0]}.csv"
            logging.info(f"Reading data from {file_path}")
            df = pd.read_csv(file_path, index_col='date', parse_dates=True)
            
            # 按日期筛选并返回
            return df.loc[start_date:end_date]
        except FileNotFoundError:
            logging.error(f"Data file not found: {file_path}")
            return None
```

#### 在主程序中切换数据源

当您想切换数据源时，只需在主程序中修改一行代码：

```python
# from data_provider import WindDataProvider
from data_provider import CsvDataProvider # 1. 仅仅是修改导入的类

# ...

# data_provider = WindDataProvider()
data_provider = CsvDataProvider() # 2. 修改实例化的对象

# 后续所有调用 data_provider.get_data(...) 的代码完全保持不变！
# ...
```

通过这种方式，数据源的切换对主分析逻辑是透明的，这使得整个系统非常灵活且易于维护。
