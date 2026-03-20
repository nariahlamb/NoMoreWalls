# NoMoreWalls

[![Fetch Status](https://github.com/peasoft/NoMoreWalls/actions/workflows/fetch.yml/badge.svg)](https://github.com/peasoft/NoMoreWalls/actions/workflows/fetch.yml) [![Stars](https://img.shields.io/github/stars/peasoft/NoMoreWalls?style=flat)](https://github.com/peasoft/NoMoreWalls/stargazers) [![Watchers](https://img.shields.io/github/watchers/peasoft/NoMoreWalls?style=flat)](https://github.com/peasoft/NoMoreWalls/watchers) [![Forks](https://img.shields.io/github/forks/peasoft/NoMoreWalls?style=flat)](https://github.com/peasoft/NoMoreWalls/forks) [![Repo size](https://img.shields.io/github/repo-size/peasoft/NoMoreWalls)](https://github.com/peasoft/NoMoreWalls/commits) ![Vistors](https://visitor-badge.laobi.icu/badge?page_id=peasoft.NoMoreWalls) [![996.icu](https://img.shields.io/badge/link-996.icu-red.svg)](https://996.icu) [![LICENSE](https://img.shields.io/badge/license-Anti%20996-blue.svg)](https://github.com/peasoft/NoMoreWalls/blob/master/LICENSE.md) [![暮光计划](https://img.shields.io/badge/link-暮光计划--向戒网瘾学校宣战-red.svg)](https://proj3ctaurora.tilda.ws/)

自动抓取合并互联网上的公开节点。

## 公告

没有节点怎么办？Windows 设备推荐使用 [SpaceTimee/Sheas-Cealer](https://github.com/SpaceTimee/Sheas-Cealer)，一键直连各种网站！

**本项目提供的订阅包含我们精心设计的分流规则，Google Play 软件秒下，自动识别被墙域名，只需将 `🐟 漏网之鱼` 维持在 `DIRECT` 即可！**

由于江苏电信、移动经常屏蔽未备案域名，本项目能自动识别屏蔽并分流，如果你仍然遇到跳转反诈中心，请将 `❓ 疑似国内` 切换为 `🚀 选择代理`。

本项目拒绝为**流氓资本家**提供任何服务！特别的，项目的许可证**严格禁止**实行 996 工作制的公司使用本项目！

由于 [BootCDN/Staticfile 已被病毒公司收购](https://www.52pojie.cn/thread-1944970-1-1.html)，我们拦截了这些网站。

如果您访问部分网站时遇到问题，可以将 `病毒网站` 分类切换为 `DIRECT`，但是您需要**自行承担一切安全风险，包括但不限于广告骚扰，账号被盗，设备中毒**等，请三思而后行！！！

为防止失联，我们建立了镜像：<https://peasoft.github.io/NWalls.html>

公开仓库当前只保留引用入口；抓取配置与完整结果通过 GitHub Gist 分发，不再直接依赖仓库内的 `list*` / `snippets` 产物。

此项目现已添加“反 996 许可证”，请各位使用者**不要违法违规要求别人加班，自觉遵守《中华人民共和国劳动法》及其它法律法规**！

### 为什么 *不要* 使用付费节点？

1. 付费节点存在付完费厂商立即跑路的**诈骗风险**，且一旦被骗钱款**无法追回**！
2. 付费节点需要注册账号并付费，厂商可以借此收集你的**个人信息**然后倒卖！付费节点管理程序可能**存在漏洞**，■■黑客也可能把你的个人信息提交给■■。
3. 付费节点数量少，一旦封禁死亡率就是 100%。与其花**几倍的钱**购买多个机场备用，不如使用本项目收集的**全网各处**公开的节点，总数是付费订阅的 10 倍，**总有不少节点存活**！
4. 现在免费节点的质量并不差，Hysteria 节点**秒开 4K 不是梦**！![秒开 4K](https://github.com/user-attachments/assets/ea73db01-e7bf-4e31-a06f-13c91e9ee87c)


## 使用方法

公开订阅入口以 `public_refs/subscriptions.md` 为准。仓库不再承载直接可用的 `list.txt`、`list.meta.yml`、`snippets/*.yml` 原始产物，所有真实内容都由 GitHub Gist 分发。

## 免责声明

订阅节点仅作学习交流使用，用于查找资料，学习知识，不做任何违法行为。所有资源均来自互联网，仅供大家交流学习使用，出现违法问题概不负责。**做出违法行为需要承担法律责任，侥幸逃脱是不可能的**！~~为阻止违法行为，本项目随时可以停止运行~~ 本项目可以采取各种技术手段来尽力阻止违法行为。

## 开发提示

由于本仓库的完整 Commit 历史极大（见页顶 repo size），如果要克隆本仓库，请使用：

```bash
git clone https://github.com/peasoft/NoMoreWalls.git --depth=1
```

如果本地仓库长期未更新，请删除仓库并重新克隆来同步最新更改，不要使用 `git pull`。

## 本地节点优化

项目已支持本地节点质量优化流程，入口脚本：

- `python optimize_local.py --passive-only`
- `python optimize_local.py --full-probe --mihomo-path <path> --reuse-cache`
- `python optimize_local.py --report-only`

推荐顺序：

1. `python fetch.py`
2. `python optimize_local.py --passive-only`
3. `python optimize_local.py --full-probe --mihomo-path <path> --reuse-cache`

运行脚本：

- PowerShell 抓取：`./scripts/run-fetch-local.ps1`
- PowerShell 优化：`./scripts/run-optimize-local.ps1 --passive-only`
- WSL/Linux 优化：`./scripts/run-optimize-local.sh --passive-only`

完整说明见 [docs/local-optimization.md](docs/local-optimization.md)。

## Gist 同步

项目已支持在 GitHub Actions 中把抓取配置、公开结果和私有诊断结果分别通过 Gist 管理。

需要的仓库配置：

- Secret：`GIST_TOKEN`
  - 建议使用经典 PAT，至少包含 `gist` 和 `repo` 权限
- Actions Variable：`CONFIG_GIST_ID`
  - 私有配置 Gist 里的文件名必须使用扁平名称，不能带 `/`
  - 至少包含 `sources.list`、`sources.fansiphone.whitelist.list`、`config.yml`、`abpwhite.txt`、`snippets_d___config.yml`、`snippets_d_example.yml`
  - 其中 `snippets_d___config.yml` 对应仓库内 `snippets/_config.yml`，`snippets_d_example.yml` 对应 `snippets/example.yml`
- Actions Variable：`RESULT_GIST_ID`
  - 公开结果 Gist，可以留空，首次运行会自动创建并写回
- Actions Variable：`PRIVATE_RESULT_GIST_ID`
  - 私有诊断 Gist，可选；用于保存 `list_raw.txt`、`list_result.csv`、`artifacts/quality/*`

公开结果 Gist 会同步：

- `list.txt`
- `list.yml`
- `list.meta.yml`
- `snippets/nodes*.yml`
- `snippets/adblock.yml`
- `snippets/direct.yml`
- `snippets/malware.yml`
- `snippets/proxy.yml`
- `snippets/region.yml`
- `snippets/rules.yml`
- `snippets/rules_online.yml`

私有诊断 Gist 会同步：

- `list_raw.txt`
- `list_result.csv`
- `artifacts/quality/*`

本地也可以手动执行：

```bash
python sync_gist.py
```

## 私有主仓库 + 公开引用模式

如果你希望把 `sources` 和完整产物都放到私有侧，而公开仓库只暴露引用链接，可以使用下面的结构：

1. 配置通过 `CONFIG_GIST_ID` 指向的私有 Gist 在运行时恢复到工作区。
2. 抓取后的公开结果通过 `RESULT_GIST_ID` 写入公开 Gist。
3. 抓取后的内部诊断结果通过 `PRIVATE_RESULT_GIST_ID` 写入私有 Gist。
4. 仓库只提交 `public_refs/` 中的引用文件，不再提交 `list*`、`snippets/`、`artifacts/quality/`。

### Workflow 开关

`fetch.yml` 新增了 `PUBLIC_REF_ONLY`（Actions Variable）：

- `PUBLIC_REF_ONLY=false`（默认）：恢复私有配置 + 抓取 + 同步 Gist + 更新引用清单。
- `PUBLIC_REF_ONLY=true`：跳过抓取，仅根据现有 `RESULT_GIST_ID` 更新公开引用清单。

### 引用清单文件

工作流会生成：

- `public_refs/index.json`：仅公开允许分发的结果链接映射
- `public_refs/subscriptions.md`：常用订阅与关键 snippets 引用

本地也可以手动生成：

```bash
python generate_public_refs.py --gist-id <你的_gist_id>
```

## 一些题外话

各位看一看：

- **[油罐车事件是最好的照妖镜，上赶着带节奏都是谁请大家记下来。](https://www.bilibili.com/video/BV1p1421b7Ki)私有化愈发严重影响的是所有中国人的切身利益，必须用公有平衡私有我们才有发展的前途。**

上方事件的严重性已经远超下面的事情了。

- **[【独家恢复】我们的教育弄虚作假，到底是为了什么](https://peasoft.github.io/2023/08/26/cnedu.html)：如此视频，为何惨遭删除？我们恢复了这段视频，只为让更多人可以看清现实。**
- **[最流氓的软件可以流氓到什么程度？](https://www.zhihu.com/question/29129310)我翻开其他网页一查，歪歪斜斜的每页上都写着“危险网页”几个字。我横竖睡不着，仔细看了半夜，才从字缝里看出字来，满本都写着两个字是“霸权”！**
- **[百度？百毒！](https://user.guancha.cn/main/content?id=100552)魏则西去世3周年：害死他的百度广告和莆田系医院**
- **[《满江红》的行为艺术](https://www.bilibili.com/video/BV11v4y1t7Gw/)：秦桧竟是我自己？**
- **[「 深蓝洞察 」2022 年度最“不可赦”漏洞](https://mp.weixin.qq.com/s/P_EYQxOEupqdU0BJMRqWsw)：知名互联网厂商(TMD并夕夕)持续挖掘新的安卓 OEM 相关漏洞，在其公开发布的 App 中实现对目前市场主流手机系统的漏洞攻击**（[具体分析](https://mp.weixin.qq.com/s/kiLvnJSDZpYRHI_XiUx9gg)）~~现已被工信部提名~~
- **[暑假学校敢补课？举报！](https://www.bilibili.com/video/BV1Vk4y1K79B)**
- **[逃离戒网瘾学校？我们找到办法了](https://www.bilibili.com/video/BV1Mg4y1A7bE)：希望你永远用不到。**
- **[一学校扔掉学生百余份外卖](https://www.bilibili.com/video/BV1a14y1S7n6)：涉嫌违法！**
- **[没收违法所得的合法性与合理性基础欠缺——简评承德程序员事件](https://www.dehenglaw.com/CN/tansuocontent/0008/029562/7.aspx?MID=0902)**
- **[【BootCDN/Staticfile投毒分析】供应链投毒后，我们的选择还剩下哪些？](https://www.52pojie.cn/thread-1944970-1-1.html)**
- 未完待续……

## Star History

<a href="https://star-history.com/#peasoft/NoMoreWalls">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=peasoft/NoMoreWalls&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=peasoft/NoMoreWalls" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=peasoft/NoMoreWalls" />
  </picture>
</a>
