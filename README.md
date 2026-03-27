<div align="center">
<a href="https://github.com/czxieddan/astrbot_plugin_jmcomic_crawler/">
  <img src="https://github.com/czxieddan/astrbot_plugin_jmcomic_crawler/raw/main/logo.png" height="200" alt="JMComic Crawler Logo">
</a>
<h1>JMComic互动抓取器 - CzXieDdan</h1>
<p><strong>面向 AstrBot 的 JMComic 数据交互与下载插件</strong><br>
通过 LLM 自然语言调用查询 JMComic 元数据、评论、总结、推荐与下载任务，并支持配置池轮询、依赖自检、公共 API 对外复用。</p>
</div>

<div align="center">
<p>
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-AGPL%20v3-ff3a68?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/github/stars/czxieddan/astrbot_plugin_jmcomic_crawler?style=for-the-badge&color=ffd700" alt="Stars">
  <img src="https://img.shields.io/badge/Platform-AstrBot-lightgrey?style=for-the-badge&color=fee888" alt="Platform">
</p>
</div>

---

## ✨ 项目特色

> 不只是一个冰冷命令插件，而是一个可交互的 **JMComic互动抓取器**。

<table>
  <tr>
    <td width="50%">
      <h3>数据抓取保完整</h3>
      <p>支持搜索、本子详情、章节详情、评论读取与上下文补全，适合聊天式连续查询。</p>
    </td>
    <td width="50%">
      <h3>下载调度保稳定</h3>
      <p>支持本子、章节、批量下载任务，具备并发控制、失败重试、取消与状态持久化能力。</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>评论总结保可读</h3>
      <p>可对内容与评论进行摘要、情感分析与相似作品推荐，并统一走 LLM 人设化输出链路。</p>
    </td>
    <td width="50%">
      <h3>配置持久保不丢</h3>
      <p>账号池、域名池、代理池轮询状态持久化，插件升级或重启后仍可延续当前运行状态。</p>
    </td>
  </tr>
  <tr>
    <td width="50%">
      <h3>自然调用保人情</h3>
      <p>已提供完整 AstrBot LLM Tool，可直接通过自然语言触发查询、总结、推荐与任务操作。</p>
    </td>
    <td width="50%">
      <h3>池内轮换保可用</h3>
      <p>账号对、域名、代理失败时自动轮询切换，并保持用户名与密码一一绑定，不会串号。</p>
    </td>
  </tr>
</table>

---

## 安装方式

将插件目录放入 AstrBot 插件目录后，在 AstrBot 后台启用插件。

依赖如下：

- Python 3.10+
- AstrBot
- jmcomic
- httpx

插件支持启动时自动检查 `requirements.txt` 中声明的依赖，并在允许时自动安装缺失依赖及其依赖。

如果你希望手动安装，可执行：

```bash
pip install -r requirements.txt
```

---

## 配置项说明

插件配置由 AstrBot 插件配置页和运行时持久配置共同组成。  
关键运行状态会镜像保存到数据目录，避免升级后丢失。

### 1. `jm_usernames`

- 类型：列表
- 说明：JM 账号用户名列表
- 要求：
  - 必须与 `jm_passwords` 一一对应
  - 两个数组长度必须一致
- 示例：

```text
["user_a", "user_b"]
```

### 2. `jm_passwords`

- 类型：列表
- 说明：JM 账号密码列表
- 要求：
  - `jm_passwords[i]` 必须对应 `jm_usernames[i]`
- 示例：

```text
["pass_a", "pass_b"]
```

### 3. `jm_domains`

- 类型：列表
- 说明：JM 域名池，调用失败时可轮询切换
- 示例：

```text
["https://domain-a.example", "https://domain-b.example"]
```

### 4. `proxy_pool`

- 类型：列表
- 说明：代理池，支持失败后切换下一个代理
- 示例：

```text
["http://127.0.0.1:7890", "http://127.0.0.1:7891"]
```

### 5. `admin_users`

- 类型：列表
- 说明：管理员用户 ID 列表
- 作用：
  - 限制下载、批量任务、取消任务等敏感操作

### 6. `cache_enabled`

- 类型：布尔
- 说明：是否启用缓存
- 默认值：`true`

### 7. `cache_ttl_seconds`

- 类型：整数
- 说明：缓存有效期（秒）
- 默认值：`300`

### 8. `memory_enabled`

- 类型：布尔
- 说明：是否启用上下文记忆
- 默认值：`true`

### 9. `memory_ttl_seconds`

- 类型：整数
- 说明：上下文记忆有效期（秒）
- 默认值：`3600`

### 10. `download_root_dir`

- 类型：字符串
- 说明：下载内容落盘目录

### 11. `download_zip_by_default`

- 类型：布尔
- 说明：是否默认创建 zip 压缩包
- 默认值：`false`

### 12. `max_concurrent_downloads`

- 类型：整数
- 说明：下载任务最大并发数
- 默认值：`2`

### 13. `download_retry_count`

- 类型：整数
- 说明：下载失败重试次数
- 默认值：`3`

### 14. `download_timeout_seconds`

- 类型：整数
- 说明：单个下载任务超时时间
- 默认值：按配置文件定义

### 15. `comments_enabled`

- 类型：布尔
- 说明：是否启用评论读取能力

### 16. `summary_enabled`

- 类型：布尔
- 说明：是否启用总结能力

### 17. `sentiment_enabled`

- 类型：布尔
- 说明：是否启用评论情感分析能力

### 18. `recommend_enabled`

- 类型：布尔
- 说明：是否启用相似作品推荐能力

### 19. `workflow_enabled`

- 类型：布尔
- 说明：是否启用多步工作流能力

### 20. `llm_postprocess_enabled`

- 类型：布尔
- 说明：是否启用 LLM 二次润色输出

### 21. `llm_persona_style_prompt`

- 类型：字符串
- 说明：LLM 人设输出风格提示词

### 22. `dependency_check_on_startup`

- 类型：布尔
- 说明：插件启动时是否检查依赖
- 默认值：`true`

### 23. `auto_install_dependencies`

- 类型：布尔
- 说明：缺失依赖时是否自动安装
- 默认值：`true`

### 24. `dependency_install_timeout_seconds`

- 类型：整数
- 说明：依赖安装超时时间（秒）

---

## 配置优先级

插件运行时配置优先级如下：

```text
默认配置 < runtime_state / dependency_state 持久状态 < AstrBot 当前非空配置
```

这意味着：

- AstrBot 后台当前填写的非空配置会优先生效
- 运行时池索引、依赖检查状态会写入数据目录
- 升级插件后，轮询状态与部分运行状态不容易丢失

---

## 指令大全

### 基础查询

- `/jm 搜索 [关键词]`
  - 按关键词搜索本子
- `/jm 本子 [album_id]`
  - 查询本子详情
- `/jm 章节 [chapter_id]`
  - 查询章节详情
- `/jm 帮助`
  - 查看帮助

### 评论 / 总结 / 推荐

- `/jm 评论本子 [album_id]`
  - 读取本子评论
- `/jm 评论章节 [chapter_id]`
  - 读取章节评论
- `/jm 情感分析 [album_id]`
  - 分析本子评论情感倾向
- `/jm 总结本子 [album_id]`
  - 总结本子内容与评论
- `/jm 总结章节 [chapter_id]`
  - 总结章节内容与评论
- `/jm 推荐 [album_id]`
  - 推荐相似作品

### 下载与任务管理

- `/jm 下载本子 [album_id]`
  - 创建本子下载任务
- `/jm 下载章节 [chapter_id]`
  - 创建章节下载任务
- `/jm 批量下载本子 [id1,id2,id3]`
  - 创建批量本子下载任务
- `/jm 任务列表`
  - 查看当前任务列表
- `/jm 任务状态 [task_id]`
  - 查看任务状态
- `/jm 取消任务 [task_id]`
  - 取消任务

### 工作流

- `/jm 工作流 [目标描述]`
  - 执行多步工作流，例如：
    - 先看评论再总结
    - 先总结再推荐
    - 基于当前上下文创建下载任务

---

## 自然语言调用说明

插件提供了完整的 AstrBot LLM Tool，可在启用函数调用能力时直接自然语言提问。

### 可自然语言触发的常见查询

- 帮我搜一下人妻题材的 JM 本子
- 看看这个本子的详情
- 把这个章节的内容总结一下
- 读取一下这个本子的评论
- 分析一下这个本子的评论情绪
- 推荐几个和这个本子类似的作品
- 帮我下载这个本子
- 看看我刚刚创建的任务现在怎么样
- 先看评论再帮我总结

### 已提供的 LLM Tool 方向

- 本子搜索
- 本子详情查询
- 章节详情查询
- 本子评论读取
- 章节评论读取
- 本子总结
- 章节总结
- 相似作品推荐
- 评论情感分析
- 下载任务创建 / 查询 / 取消
- 多步工作流执行

---

## 公共 API 调用说明

当前插件已暴露稳定公共接口，其他插件可以通过插件实例调用：

```python
jm_plugin = ...
api = jm_plugin.get_public_api()
```

### 结构化接口示例

```python
result = await api.search_album_structured("人妻", page=1)
detail = await api.album_detail_structured("123456")
comments = await api.album_comments_structured("123456", limit=10)
task = await api.create_album_download_task_structured(
    "123456",
    requested_by="plugin_x",
    create_zip=False,
)
```

### LLM 友好文本接口示例

```python
text = await api.album_summary_text(event, "123456")
recommend = await api.recommend_text(event, "123456")
workflow = await api.workflow_text(event, "先看评论再总结", album_id="123456")
```

### 当前对外接口类型

- `*_structured(...)`
  - 返回结构化数据
  - 适合其他插件二次处理、渲染或喂给自己的 LLM
- `*_text(...)`
  - 返回适合聊天场景直接输出的文本
  - 内部会复用本插件已有的总结、推荐、工作流与人设化输出链路

---

## 轮询与持久化说明

插件内部会把配置归一化为：

- 账号对池：`[{username, password}, ...]`
- 域名池：`[domain1, domain2, ...]`
- 代理池：`[proxy1, proxy2, ...]`

```text
data/config/runtime_state.json
```

---

## 依赖自检说明

插件启动时会优先检查 `requirements.txt` 中声明的依赖是否可导入。

默认行为：

- 启动时检查依赖
- 若缺失依赖，自动执行：

```bash
python -m pip install -r requirements.txt
```

- pip 会自动安装依赖的依赖
- 检查与安装状态会写入：

```text
data/config/dependency_state.json
```

---

## 开源协议

<a href="https://gnu.ac.cn/licenses/agpl-3.0.html">
 <img src=https://gnu.ac.cn/graphics/agplv3-with-text-162x68.png alt="GNU Affero General Public License v3.0 (AGPL v3)">
</a>

本项目采用 **GNU Affero General Public License v3.0 (AGPL v3)** 开源协议。

这意味着：

- 你可以在遵守 AGPL v3 的前提下使用、修改与再分发本项目
- 如果你基于本项目进行修改并提供服务，相关源代码仍需按 AGPL v3 要求向用户开放

---

<div align="center">
  <h3>👥 Contributors</h3>
  <a href="https://github.com/czxieddan/astrbot_plugin_jmcomic_crawler/graphs/contributors">
    <img src="https://stg.contrib.rocks/image?repo=czxieddan/astrbot_plugin_jmcomic_crawler" />
  </a>
</div>

---

<div align="center">
  <a href="https://star-history.com/#czxieddan/astrbot_plugin_jmcomic_crawler&Date">
    <img src="https://api.star-history.com/svg?repos=czxieddan/astrbot_plugin_jmcomic_crawler&type=Date" alt="Star History Chart" />
  </a>
</div>


