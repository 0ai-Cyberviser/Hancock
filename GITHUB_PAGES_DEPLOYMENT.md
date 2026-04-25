# 🌐 GITHUB PAGES DEPLOYMENT GUIDE

**Deploy all CyberViser AI project sites to GitHub Pages**

**Created:** April 25, 2026  
**Status:** ✅ READY FOR DEPLOYMENT  
**Author:** HancockForge (0AI / CyberViser)

---

## 📋 OVERVIEW

This guide walks you through deploying the 4 individual project sites to GitHub Pages:

1. **🍑 PeachTrace** → `https://cyberviser.github.io/Hancock/peachtrace/`
2. **🌳 PeachTree** → `https://0ai-cyberviser.github.io/PeachTree/`
3. **🌵 CactusFuzz** → `https://0ai-cyberviser.github.io/cactusfuzz/`
4. **🍑 PeachFuzz** → `https://0ai-cyberviser.github.io/peachfuzz/`

---

## 🎯 DEPLOYMENT OPTIONS

### Option A: Deploy from Hancock repo (PeachTrace)

PeachTrace lives inside the Hancock repo, so it deploys as a subdirectory:

```bash
cd /home/_0ai_/Hancock-1

# Copy docs/ to root for GitHub Pages
cp -r docs/ ./

# Commit and push
git add docs/
git commit -m "feat: Add PeachTrace v9.10 landing page"
git push origin main

# Enable GitHub Pages
# 1. Go to https://github.com/cyberviser/Hancock/settings/pages
# 2. Source: "Deploy from a branch"
# 3. Branch: main
# 4. Folder: /docs
# 5. Save

# Site will be live at:
# https://cyberviser.github.io/Hancock/peachtrace/
```

**Verification:**
```bash
# Test locally first
cd docs/peachtrace/
python3 -m http.server 8000
# Open http://localhost:8000 in browser
```

---

### Option B: Deploy standalone repos (PeachTree, CactusFuzz, PeachFuzz)

Each standalone project gets its own GitHub repo and GitHub Pages site.

#### 1. PeachTree Deployment

```bash
# Navigate to PeachTree repo (or create it)
cd /home/_0ai_/PeachTree
# If repo doesn't exist, initialize it:
# git init && git remote add origin https://github.com/0ai-Cyberviser/PeachTree.git

# Copy site files to docs/
mkdir -p docs
cp /home/_0ai_/Hancock-1/docs/peachtree/index.html docs/

# Commit and push
git add docs/
git commit -m "feat: Add PeachTree landing page"
git push origin main

# Enable GitHub Pages
# 1. Go to https://github.com/0ai-Cyberviser/PeachTree/settings/pages
# 2. Source: "Deploy from a branch"
# 3. Branch: main
# 4. Folder: /docs
# 5. Save

# Site will be live at:
# https://0ai-cyberviser.github.io/PeachTree/
```

#### 2. CactusFuzz Deployment

```bash
# Navigate to peachfuzz repo (monorepo with both fuzzers)
cd /home/_0ai_/peachfuzz
# If repo doesn't exist:
# git init && git remote add origin https://github.com/0ai-Cyberviser/peachfuzz.git

# Copy site files
mkdir -p docs/cactusfuzz
cp /home/_0ai_/Hancock-1/docs/cactusfuzz/index.html docs/cactusfuzz/

# Commit and push
git add docs/cactusfuzz/
git commit -m "feat: Add CactusFuzz red team landing page"
git push origin main

# Enable GitHub Pages (same as above)
# Site will be live at:
# https://0ai-cyberviser.github.io/cactusfuzz/
```

#### 3. PeachFuzz Deployment

```bash
# Same peachfuzz repo
cd /home/_0ai_/peachfuzz

# Copy site files
mkdir -p docs/peachfuzz
cp /home/_0ai_/Hancock-1/docs/peachfuzz/index.html docs/peachfuzz/

# Or use root docs/ for main landing page:
cp /home/_0ai_/Hancock-1/docs/peachfuzz/index.html docs/index.html

# Commit and push
git add docs/
git commit -m "feat: Add PeachFuzz blue team landing page"
git push origin main

# Site will be live at:
# https://0ai-cyberviser.github.io/peachfuzz/
```

---

## 🔗 UPDATE GITHUB REPO SETTINGS

After deploying, update each repo's settings:

### Repository Homepage URL

For each repo, add the GitHub Pages URL as the homepage:

```bash
# PeachTree
# 1. Go to https://github.com/0ai-Cyberviser/PeachTree
# 2. Click "About" gear icon (top right)
# 3. Website: https://0ai-cyberviser.github.io/PeachTree/
# 4. Check "Use your GitHub Pages website"
# 5. Save

# Repeat for all repos
```

### Repository Description

Update descriptions to match:

- **PeachTrace:** "🍑 OSINT Prime Sentinel v9.10 - 400x faster reconnaissance than human teams"
- **PeachTree:** "🌳 Dataset Orchestrator for AI Security Training - Quality Control + Provenance"
- **CactusFuzz:** "🌵 Red Team Offensive Fuzzer - Authorized Lab Use Only"
- **PeachFuzz:** "🍑 Blue Team Defensive Fuzzer - CI/CD Safe Parser Testing"

### Repository Topics

Add relevant topics (GitHub tags) for discoverability:

**PeachTrace:**
```
osint, reconnaissance, subdomain-enumeration, rustscan, kali-linux, pentesting, cybersecurity
```

**PeachTree:**
```
dataset, machine-learning, fine-tuning, ai-training, data-quality, jsonl, deduplication
```

**CactusFuzz:**
```
fuzzing, offensive-security, red-team, penetration-testing, vulnerability-research
```

**PeachFuzz:**
```
fuzzing, defensive-security, blue-team, ci-cd, parser-testing, atheris, libfuzzer
```

---

## 🧪 LOCAL TESTING

Test all sites locally before deployment:

```bash
# PeachTrace
cd /home/_0ai_/Hancock-1/docs/peachtrace
python3 -m http.server 8001 &

# PeachTree
cd /home/_0ai_/Hancock-1/docs/peachtree
python3 -m http.server 8002 &

# CactusFuzz
cd /home/_0ai_/Hancock-1/docs/cactusfuzz
python3 -m http.server 8003 &

# PeachFuzz
cd /home/_0ai_/Hancock-1/docs/peachfuzz
python3 -m http.server 8004 &

# Open in browser:
# http://localhost:8001 - PeachTrace
# http://localhost:8002 - PeachTree
# http://localhost:8003 - CactusFuzz
# http://localhost:8004 - PeachFuzz

# Test navigation, links, responsiveness
# Kill servers when done:
killall python3
```

---

## ✅ POST-DEPLOYMENT CHECKLIST

After all sites are live:

### 1. Verify All URLs

- [ ] https://cyberviser.github.io/Hancock/peachtrace/ → PeachTrace live
- [ ] https://0ai-cyberviser.github.io/PeachTree/ → PeachTree live
- [ ] https://0ai-cyberviser.github.io/cactusfuzz/ → CactusFuzz live
- [ ] https://0ai-cyberviser.github.io/peachfuzz/ → PeachFuzz live

### 2. Cross-Link Verification

Test footer navigation on each site:
- Click "Hancock" → Should go to main Hancock site
- Click "PeachTrace" → Should go to PeachTrace site
- Click "PeachTree" → Should go to PeachTree site
- Click "CactusFuzz" → Should go to CactusFuzz site
- Click "PeachFuzz" → Should go to PeachFuzz site
- Click "Main Hub" → Should go to cyberviserai.com

### 3. Mobile Responsiveness

Test on mobile devices:
- [ ] Hero sections scale properly
- [ ] Navigation collapses on mobile
- [ ] Feature cards stack vertically
- [ ] Terminal demos remain readable
- [ ] Buttons are tap-friendly

### 4. Performance Check

Run Lighthouse audits:
```bash
# Install Lighthouse CLI
npm install -g lighthouse

# Audit each site
lighthouse https://cyberviser.github.io/Hancock/peachtrace/ --view
lighthouse https://0ai-cyberviser.github.io/PeachTree/ --view
lighthouse https://0ai-cyberviser.github.io/cactusfuzz/ --view
lighthouse https://0ai-cyberviser.github.io/peachfuzz/ --view

# Target scores:
# Performance: 90+
# Accessibility: 90+
# Best Practices: 90+
# SEO: 90+
```

### 5. Update Main Sites

Update existing sites to link to new pages:

**Hancock Site (cyberviser.github.io/Hancock/):**
- Add "PeachTrace" link in navigation
- Update features section to mention PeachTrace

**cyberviserai.com:**
- Update ecosystem page with all 4 project links
- Add PeachTrace to Hancock ecosystem section
- Verify all footer links point to correct URLs

---

## 🚀 CONTINUOUS DEPLOYMENT (OPTIONAL)

Set up automatic deployment with GitHub Actions:

**`.github/workflows/deploy-pages.yml`:**
```yaml
name: Deploy GitHub Pages

on:
  push:
    branches:
      - main
    paths:
      - 'docs/**'

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Pages
        uses: actions/configure-pages@v3
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v2
        with:
          path: 'docs/'
      
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v2
```

This auto-deploys whenever you push changes to `docs/`.

---

## 🔧 TROUBLESHOOTING

### Site Not Loading

1. **Check GitHub Pages Settings:**
   - Go to repo Settings → Pages
   - Verify "Source" is set to main branch, /docs folder
   - Wait 2-5 minutes after first deployment

2. **Check File Paths:**
   - Ensure `index.html` exists in the correct directory
   - Verify paths in HTML are relative (not absolute)

3. **Check Build Status:**
   - Go to repo Actions tab
   - Look for "pages build and deployment" workflow
   - Click for error details if failed

### Links Not Working

1. **Update Footer Links:**
   - All footer links must use full URLs (https://...)
   - No relative paths for cross-site links

2. **Test Each Link:**
   ```bash
   # Test all links from each page
   wget --spider --recursive --no-directories --no-verbose \
     https://cyberviser.github.io/Hancock/peachtrace/
   ```

### CSS Not Loading

1. **Check CSS Inline:**
   - All sites use inline `<style>` tags (no external CSS files)
   - Should work immediately

2. **Clear Browser Cache:**
   - Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)

---

## 📊 ANALYTICS (OPTIONAL)

Add privacy-respecting analytics to track visitors:

**Plausible Analytics (recommended):**
```html
<!-- Add before </head> on each page -->
<script defer data-domain="cyberviser.github.io" src="https://plausible.io/js/script.js"></script>
```

**Google Analytics (if needed):**
```html
<!-- Add before </head> on each page -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

---

## 🎉 LAUNCH CHECKLIST

Before announcing the new sites:

- [ ] All 4 sites deployed and accessible
- [ ] All cross-links working
- [ ] Mobile responsiveness verified
- [ ] Lighthouse scores 90+ across all sites
- [ ] GitHub repo descriptions updated
- [ ] GitHub repo topics added
- [ ] Homepage URLs set in repo settings
- [ ] Main Hancock site updated with PeachTrace link
- [ ] cyberviserai.com updated with all project links
- [ ] Social media graphics prepared (optional)
- [ ] Blog post written announcing sites (optional)

---

## 📝 NEXT STEPS

After deployment:

1. **Update ROADMAP.md** in Hancock repo:
   ```markdown
   ## Phase 3: Web Ecosystem (April 2026) ✅
   - [x] PeachTrace v9.10 landing page
   - [x] PeachTree dataset engine site
   - [x] CactusFuzz red team site
   - [x] PeachFuzz blue team site
   - [ ] Enhanced cyberviserai.com hub (next)
   - [ ] Web3 integration (planned)
   ```

2. **Create GitHub Release:**
   - Tag: `v0.4.0-web-ecosystem`
   - Title: "Web Ecosystem Launch - Individual Project Sites"
   - Description: Links to all 4 new sites

3. **Social Media Announcements:**
   - Twitter/X thread showcasing each project
   - LinkedIn post with professional screenshots
   - Reddit r/netsec post (if appropriate)

---

## 🏆 SUCCESS METRICS

Track these after launch:

**Week 1:**
- Unique visitors per site
- Average time on page
- GitHub stars increase
- GitHub issues/questions

**Month 1:**
- Total page views across all sites
- Referral sources (where visitors come from)
- Mobile vs desktop split
- Most popular pages/sections

**Quarter 1:**
- GitHub stars target: 500+ across all repos
- Documentation views: 5,000+ total
- User feedback and improvements

---

**🍑 Ready to deploy the complete CyberViser AI web ecosystem!**

**Next:** Deploy sites → Test all links → Enhance cyberviserai.com hub → Add Web3 integration

**Built by:** HancockForge (Johnny Watters / 0AI / CyberViser)  
**Date:** April 25, 2026
