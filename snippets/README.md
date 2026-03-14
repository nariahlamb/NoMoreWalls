# 配置片段

这里存放了一些从 `list.yml` 中拆分出的配置片段，用于将本项目提供的一些配置整合到其它配置中。

# 文件说明

## Proxy Providers 规则集

- [nodes.yml](./nodes.yml)：节点列表，注意**不要**和下文的 `proxy.yml` 搞混了。
- [nodes.meta.yml](./nodes.meta.yml)：适用于 Meta 核心的节点列表。
- `nodes_JP.yml` / `nodes_JP.meta.yml`
- `nodes_US.yml` / `nodes_US.meta.yml`
- `nodes_GB.yml` / `nodes_GB.meta.yml`
- `nodes_SG.yml` / `nodes_SG.meta.yml`
- `nodes_TW.yml` / `nodes_TW.meta.yml`
- `nodes_HK.yml` / `nodes_HK.meta.yml`

以上 6 组为当前公开保留的地区分类片段；其它地区和非地区分类不再单独拆分输出。

## Rule Providers 规则集

- [adblock.yml](./adblock.yml)：广告屏蔽域名列表。
- [proxy.yml](./proxy.yml)：需要走代理的域名列表。
- [direct.yml](./direct.yml)：需要直连的域名列表。
- [region.yml](./region.yml)：存在锁区的域名列表。

注意：广告拦截列表中的域名不会出现在需要走代理的域名列表中，因此即使您没有使用广告屏蔽规则，仍有一些广告会无法加载。

# 配置示例

```yaml
proxy-providers:
  订阅地址:
    type: http
    url: "https://mirror.ghproxy.com/https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/nodes.yml"
    interval: 3600
    path: ./proxy_providers/NoMoreWalls.yml
    health-check:
      enable: true
      interval: 600
      url: https://www.google.com/

rule-providers:
  adblock:
    type: http
    behavior: classical
    path: ./rule_providers/adblock.yml
    url: "https://mirror.ghproxy.com/https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/adblock.yml"
    interval: 21600 #6h
    format: yaml
  proxy:
    type: http
    behavior: classical
    path: ./rule_providers/proxy.yml
    url: "https://mirror.ghproxy.com/https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/proxy.yml"
    interval: 86400 #24h
    format: yaml
  direct:
    type: http
    behavior: classical
    path: ./rule_providers/direct.yml
    url: "https://mirror.ghproxy.com/https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/direct.yml"
    interval: 86400 #24h
    format: yaml
  region:
    type: http
    behavior: classical
    path: ./rule_providers/region.yml
    url: "https://mirror.ghproxy.com/https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/region.yml"
    interval: 86400 #24h
    format: yaml

rules:
    - DOMAIN-SUFFIX,googleapis.cn,DIRECT
  - DOMAIN-SUFFIX,xn--ngstr-lra8j.com,DIRECT # Google Play 国外/国内 服务器，多数可直连，连不上 Google Play 会自动更换
  - DOMAIN-SUFFIX,xn--ngstr-cn-8za9o.com,DIRECT # Google Play 纯国内 服务器，似乎没啥卵用？
  - IP-CIDR,61.160.148.90/32,❓ 疑似国内 # 可能被江苏反诈污染
  - DOMAIN-KEYWORD,fastgit,DIRECT
  - DOMAIN-KEYWORD,fgit,DIRECT
  - DOMAIN-KEYWORD,ghproxy,DIRECT
  - DOMAIN-SUFFIX,zzko.cn,DIRECT
  - DOMAIN-SUFFIX,jsdelivr.us,DIRECT
  - DOMAIN-SUFFIX,jsdelivr.net,DIRECT
  - RULE-SET,adblock,⛔ 广告拦截
  - DOMAIN-SUFFIX,cn,DIRECT
  - DOMAIN-KEYWORD,-cn,DIRECT
  - RULE-SET,region,🌐 突破锁区
  - RULE-SET,direct,DIRECT
  - GEOIP,CN,❓ 疑似国内
  - RULE-SET,proxy,🚀 选择代理
  - MATCH,🐟 漏网之鱼
```

# 加速链接（以节点列表为例）
- 原始链接: `https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/nodes.yml`
- JsDelivr 反代（zzko.cn）: `https://cdn.jsdelivr.us/gh/peasoft/NoMoreWalls@master/snippets/nodes.yml`
- JsDelivr Fastly CDN: `https://fastly.jsdelivr.net/gh/peasoft/NoMoreWalls@master/snippets/nodes.yml`
- JsDelivr Cloudflare CDN: `https://testingcf.jsdelivr.net/gh/peasoft/NoMoreWalls@master/snippets/nodes.yml`
- JsDelivr GCore CDN: `https://gcore.jsdelivr.net/gh/peasoft/NoMoreWalls@master/snippets/nodes.yml`
- GhProxy.com: `https://mirror.ghproxy.com/https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/snippets/nodes.yml`

以下加速链接可能无效：
- KKGithub: `https://raw.kkgithub.com/peasoft/NoMoreWalls/master/snippets/nodes.yml`
