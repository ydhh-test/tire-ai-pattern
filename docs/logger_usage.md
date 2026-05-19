# 日志模块使用指南

## 1. 概述

`src/utils/logger.py` 提供了项目标准化的日志系统，包含以下核心功能：
- 配置化的日志记录器创建
- 文件和控制台双重输出支持
- 日志级别控制（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- 类混入（Mixin）模式，方便在类中使用日志

## 2. 核心组件

### 2.1 setup_logger() - 配置日志记录器

**函数签名**：
```python
setup_logger(
    name: str = "giti_tire",
    level: str = "DEBUG", 
    log_file: Optional[str] = None,
    console_output: bool = True
) -> logging.Logger
```

**参数说明**：
- `name`: 日志记录器名称，默认为 `"giti_tire"`
- `level`: 日志级别，支持 `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"`, `"CRITICAL"`，默认为 `"INFO"`
- `log_file`: 日志文件路径（可选），如果提供则会同时输出到文件
- `console_output`: 是否输出到控制台，默认为 `True`

**使用示例**：
```python
from src.utils.logger import setup_logger

# 基本使用
logger = setup_logger()

# 自定义配置
logger = setup_logger(
    name="my_app",
    level="DEBUG",
    log_file="logs/app.log",
    console_output=True
)
```

### 2.2 get_logger() - 获取日志记录器

**函数签名**：
```python
get_logger(name: str = "giti_tire") -> logging.Logger
```

**特点**：
- 如果已存在同名记录器且已配置处理器，则直接返回
- 如果不存在或未配置，则调用 `setup_logger()` 创建新记录器
- 避免重复添加处理器的问题

**使用示例**：
```python
from src.utils.logger import get_logger

logger = get_logger("my_module")
logger.info("This is an info message")
```

### 2.3 LoggerMixin - 日志混入类

**用途**：为类提供便捷的日志功能，无需手动创建日志记录器

**使用方式**：
```python
from src.utils.logger import LoggerMixin

class MyClass(LoggerMixin):
    def do_something(self):
        self.logger.info("Doing something...")
        self.logger.error("Something went wrong!")
```

**特点**：
- `self.logger` 属性自动创建以类名为名称的日志记录器
- 每个类实例共享同一个日志记录器（基于类名）

### 2.4 default_logger - 默认日志记录器

模块在导入时自动创建一个名为 `"tire-ai-pattern"` 的默认日志记录器：

```python
from src.utils.logger import default_logger

default_logger.info("Using default logger")
```

## 3. 使用场景

### 3.1 应用程序入口点

在应用主入口配置全局日志：

```python
from src.utils.logger import setup_logger

# 配置全局日志
logger = setup_logger(
    name="tire-ai-app",
    level="INFO",
    log_file="logs/application.log"
)

logger.info("Application started")
```

### 3.2 模块级日志

在各个模块中获取专用日志记录器：

```python
# src/api/generation.py
from src.utils.logger import get_logger

logger = get_logger(__name__)

def generate_image():
    logger.debug("Starting image generation")
    # ... 业务逻辑
    logger.info("Image generation completed successfully")
```

### 3.3 类中使用日志

在类中继承 `LoggerMixin`：

```python
# src/core/processor.py  
from src.utils.logger import LoggerMixin

class ImageProcessor(LoggerMixin):
    def process(self, image_data):
        self.logger.info(f"Processing image with {len(image_data)} bytes")
        try:
            # 处理逻辑
            result = self._do_processing(image_data)
            self.logger.info("Processing completed successfully")
            return result
        except Exception as e:
            self.logger.error(f"Processing failed: {str(e)}")
            raise
```

### 3.4 异常处理中的日志

结合异常处理使用日志：

```python
from src.utils.logger import get_logger
from src.common.exceptions import RuntimeProcessError

logger = get_logger(__name__)

def risky_operation(data):
    try:
        # 可能失败的操作
        result = perform_operation(data)
        logger.info("Operation succeeded")
        return result
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}", exc_info=True)
        raise RuntimeProcessError("risky_operation", "operation failed", e)
```

## 4. 最佳实践

### 4.1 日志级别选择
- **DEBUG**: 详细的调试信息，通常只在开发环境中启用
- **INFO**: 一般信息，确认程序按预期工作
- **WARNING**: 警告信息，表示可能有问题但程序仍能继续运行
- **ERROR**: 错误信息，表示功能无法执行
- **CRITICAL**: 严重错误，可能导致程序终止

### 4.2 日志文件管理
- 建议按模块或功能组织日志文件目录
- 在生产环境中启用文件日志，在开发环境中可以只使用控制台
- 考虑日志轮转策略避免文件过大

### 4.3 性能考虑
- 避免在高频循环中记录 DEBUG 级别日志
- 对于昂贵的日志消息构造，先检查日志级别：
  ```python
  if logger.isEnabledFor(logging.DEBUG):
      logger.debug(f"Expensive operation result: {expensive_computation()}")
  ```

### 4.4 安全考虑
- 避免在日志中记录敏感信息（密码、token、个人数据等）
- 对用户输入进行适当的脱敏处理后再记录

## 5. 与项目架构集成

### 5.1 分层日志策略
- **API层**: 记录请求/响应摘要、错误信息
- **业务层**: 记录业务流程关键步骤、决策点
- **数据模型层**: 通常不需要日志，除非有复杂的验证逻辑
- **工具层**: 记录工具使用情况、性能指标

### 5.2 与异常处理集成
日志模块应与异常处理体系配合使用：
- 在捕获异常的地方记录 ERROR 级别日志
- 在抛出异常的地方提供足够的上下文信息
- 使用 `exc_info=True` 参数记录完整的异常堆栈

### 5.3 开发 vs 生产环境
- **开发环境**: 启用 DEBUG 级别，输出到控制台
- **生产环境**: 使用 INFO 或 WARNING 级别，输出到文件，考虑日志轮转

## 6. 常见问题

### 6.1 重复日志输出
如果看到重复的日志消息，通常是因为多次调用 `setup_logger()` 导致重复添加处理器。解决方案：
- 使用 `get_logger()` 而不是 `setup_logger()` 来获取已存在的记录器
- 确保在应用程序启动时只配置一次全局日志

### 6.2 日志文件目录不存在
`setup_logger()` 会自动创建日志文件的父目录，但需要确保应用程序有写入权限。

### 6.3 日志格式自定义
当前日志格式为：`%(asctime)s - %(name)s - %(levelname)s - %(message)s`
如需自定义格式，需要修改 `setup_logger()` 函数中的 `Formatter` 配置。