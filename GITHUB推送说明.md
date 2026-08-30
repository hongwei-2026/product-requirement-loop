# 推送到你的 GitHub（一次性操作）

本地仓库已 `git init` 并完成首次提交。因本机 **未登录 GitHub CLI**，需要你在自己电脑上执行下面几步（可用代理）。

## 1. 设代理（按你本机端口改）

```powershell
$env:HTTP_PROXY="http://127.0.0.1:7890"
$env:HTTPS_PROXY="http://127.0.0.1:7890"
```

## 2. 登录 GitHub

```powershell
gh auth login
```

选 GitHub.com → HTTPS → 浏览器登录。

## 3. 创建远程仓库并推送

在仓库目录 `课题申请-product-requirement-loop` 下：

```powershell
cd "D:\量潮科技\课题申请-product-requirement-loop"
gh repo create product-requirement-loop --public --source=. --remote=origin --push
```

若仓库名已占用，换一个名字，例如 `quanttide-product-requirement-loop`。

## 4. 不用 gh 的替代做法

1. 在 GitHub 网页新建空仓库 `product-requirement-loop`（不要勾选 README）  
2. 执行：

```powershell
git remote add origin https://github.com/你的用户名/product-requirement-loop.git
git push -u origin main
```

## 5. 验证

浏览器打开 `https://github.com/你的用户名/product-requirement-loop`，应能看到：

- `阶段0验收操作手册.md`
- `screenshots/stage0/` 下的验收截图
- `stage0-self-test-report.md`（26 项全通过）

推送成功后，把仓库链接发给导师即可。
