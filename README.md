相比于源库增加了仪表盘

提供了一个较为实用的仪表盘，感谢@MengNianxiaoyao 作出的美观调整

![image](https://github.com/Zuosizhu/Alas-with-Dashboard/assets/60862861/ee2e3e8f-9a19-417e-8e5f-441ecdee1ae6)

![image](https://github.com/Zuosizhu/Alas-with-Dashboard/assets/60862861/55f95cb3-5234-45d3-a265-6b5e0ab5fc3e)

![image](https://github.com/Zuosizhu/Alas-with-Dashboard/assets/60862861/6033931a-c4ea-4262-853f-f315f076d305)

![image](https://github.com/Zuosizhu/Alas-with-Dashboard/assets/60862861/6fafb159-2092-4423-9d58-3d6c1262e691)

## 环境 / Environment (uv)

本项目默认使用 uv 管理 Python 虚拟环境（.venv）。

- 安装 uv 并确认 PATH 中可用：`uv --version`
- 创建并同步环境：
	- `uv venv .venv`（或指定 Python 3.7：`uv venv --python "C:\\Python37\\python.exe" .venv`）
	- `uv pip sync -p .venv requirements.txt`
- 启动仪表盘 / Start dashboard：`./start_alas.ps1`

说明 / Notes：启动脚本会优先使用 Firefox 打开 Web UI（http://localhost:22267/），若不可用则回退至 Chrome 或系统默认浏览器；脚本也会在启动前尝试停止已运行的实例，并在缺少 .venv 时通过 uv 自动创建和同步依赖。

更多细节请参考 / See also：`agents.md`, `CLAUDE.md`
