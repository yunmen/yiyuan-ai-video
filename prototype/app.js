/* ---------- 基础导航 ---------- */
var stack = [];
var cur = 'home';
function $(s){return document.querySelector(s)}
function $$(s){return Array.prototype.slice.call(document.querySelectorAll(s))}

/* 桌面顶部导航高亮映射：流程页归入「爆款视频」 */
var NAV_GROUP = {home:'home', templates:'templates', material:'templates', generating:'templates', result:'templates', avatars:'avatars', works:'works', me:'me'};
function syncTopnav(){
  var key = NAV_GROUP[cur] || '';
  $$('.topnav-links a').forEach(function(a){
    a.classList.toggle('on', a.getAttribute('data-nav') === key);
  });
}

function go(id, back){
  if(id === cur) return;
  var from = document.getElementById('p-' + cur);
  var to = document.getElementById('p-' + id);
  if(!to) return;
  if(!back) stack.push(cur);
  from.classList.remove('active','slide-in','slide-back');
  to.classList.remove('slide-in','slide-back');
  to.classList.add('active', back ? 'slide-back' : 'slide-in');
  cur = id;
  syncTopnav();
  var body = to.querySelector('.body');
  if(body) body.scrollTop = 0;
  if(id === 'generating') startGen();
  if(id === 'result') startPlay();
  if(id === 'works') renderWorks();
}

function toast(msg){
  var t = $('#toast');
  t.textContent = msg;
  t.classList.add('on');
  clearTimeout(t._t);
  t._t = setTimeout(function(){ t.classList.remove('on') }, 1600);
}

/* ---------- 全局点击委托 ---------- */
document.addEventListener('click', function(e){
  var goEl = e.target.closest('[data-go]');
  if(goEl){
    var t = goEl.getAttribute('data-go');
    if(t === cur) return;
    // Tab 栏 / 顶部导航点击视为同层切换
    if(goEl.classList.contains('tab') || goEl.closest('.topnav')) stack = [];
    go(t);
    return;
  }
  var backEl = e.target.closest('[data-back-btn]');
  if(backEl){
    var page = backEl.closest('.page');
    var target = page.getAttribute('data-back');
    if(target && target !== cur){ stack = []; go(target, true); }
    else if(stack.length){ go(stack.pop(), true); }
    return;
  }
  var actEl = e.target.closest('[data-act]');
  if(actEl) act(actEl.getAttribute('data-act'), actEl);
});

/* ---------- 模板数据 ---------- */
var TPLS = [
  {n:'火锅店开业引流', c:'餐饮', g:['#FFB88A','#FF5A20'], d:'15秒 · 餐饮引流款'},
  {n:'烧烤店探店爆款', c:'餐饮', g:['#A9663A','#6B3A18'], d:'18秒 · 探店款'},
  {n:'奶茶店新品上新', c:'餐饮', g:['#FFC7DA','#F2739A'], d:'12秒 · 上新款'},
  {n:'小龙虾季促销',   c:'餐饮', g:['#FF9C7A','#D92B0F'], d:'15秒 · 促销款'},
  {n:'早餐店每日特价', c:'餐饮', g:['#CCE8A8','#6BB045'], d:'10秒 · 特价款'},
  {n:'家常菜馆招牌菜', c:'餐饮', g:['#FFD699','#E8873A'], d:'15秒 · 招牌款'},
  {n:'口红试色种草',   c:'美妆', g:['#FFB3C1','#E23D69'], d:'12秒 · 种草款'},
  {n:'护肤店到店福利', c:'美妆', g:['#D9F0E4','#4FB98A'], d:'15秒 · 到店款'},
  {n:'女装上新秒杀',   c:'电商', g:['#FFD6E0','#F0568C'], d:'15秒 · 秒杀款'},
  {n:'家居好物开箱',   c:'电商', g:['#FFF0C2','#E0A32E'], d:'20秒 · 开箱款'},
  {n:'理发店造型特惠', c:'本地服务', g:['#CBD8F0','#5C7FBF'], d:'15秒 · 特惠款'},
  {n:'洗车店会员卡',   c:'本地服务', g:['#BFE6F5','#2E93C8'], d:'12秒 · 会员款'}
];
var CATS = ['全部','餐饮','美妆','电商','本地服务','其他'];
var curCat = '餐饮';

function renderCats(){
  $('#cats').innerHTML = CATS.map(function(c){
    return '<div class="' + (c === curCat ? 'on' : '') + '" data-act="cat" data-v="' + c + '">' + c + '</div>';
  }).join('');
}
function renderGrid(){
  var list = TPLS.filter(function(t){ return curCat === '全部' || t.c === curCat });
  if(!list.length){
    $('#grid').innerHTML = '<div style="grid-column:1/-1;width:100%;text-align:center;padding:60px 0;color:#9B9B9B;font-size:13px">该分类模板整理中，先看看其他分类</div>';
    return;
  }
  $('#grid').innerHTML = list.map(function(t){
    return '<div class="tcard" data-act="pickTpl" data-v="' + t.n + '" data-d="' + t.d + '">' +
      '<div class="cover" style="background:linear-gradient(180deg,' + t.g[0] + ',' + t.g[1] + ')">' +
        '<div class="play"><svg width="18" height="18" viewBox="0 0 18 18"><path d="M6 3L14 9L6 15V3Z" fill="#fff"/></svg></div>' +
        '<div class="tag">做同款</div>' +
      '</div><p>' + t.n + '</p></div>';
  }).join('');
}

/* ---------- 数字人 ---------- */
var AVATARS = [
  {n:'知性小姐姐', bg:'#F3E8FF', fg:'#C4A0E8'},
  {n:'商务男士',   bg:'#E4EDFB', fg:'#8FA9D0'},
  {n:'邻家小妹',   bg:'#FFE9EF', fg:'#F5A3BC'},
  {n:'方言大叔',   bg:'#E6F4EA', fg:'#8EC49F'}
];
function renderAvatars(){
  $('#avGrid').innerHTML = AVATARS.map(function(a, i){
    return '<div class="card avcard">' +
      '<svg viewBox="0 0 143 180" width="100%" height="180"><rect width="143" height="180" rx="10" fill="' + a.bg + '"/><circle cx="71.5" cy="70" r="28" fill="' + a.fg + '"/><path d="M30 142C30 112 48 96 71.5 96C95 96 113 112 113 142V180H30V142Z" fill="' + a.fg + '"/></svg>' +
      '<div style="font-size:13px;font-weight:500;margin:8px 0">' + a.n + '</div>' +
      '<div class="' + (i === 0 ? 'up' : 'up gray') + '" style="justify-content:center;border-radius:16px;height:32px" data-act="pickAvatar">选择</div>' +
    '</div>';
  }).join('');
}

/* ---------- 我的作品 ---------- */
var WORKS = [
  {n:'火锅店开业引流', t:'今天 14:22 · 15秒', g:['#FFCDB0','#FF8347']},
  {n:'奶茶店新品上新', t:'昨天 10:05 · 12秒', g:['#BFE3CC','#4FB98A']},
  {n:'烧烤店探店爆款', t:'9月15日 19:40 · 18秒', g:['#FFD9A8','#E8873A']}
];
var emptyWorks = false;
function renderWorks(){
  var box = $('#worksBody');
  if(emptyWorks){
    box.innerHTML = '<div class="empty">' +
      '<svg width="96" height="96" viewBox="0 0 96 96"><rect x="14" y="22" width="68" height="50" rx="10" stroke="#D8DADE" stroke-width="3" fill="none"/><path d="M14 38H82" stroke="#D8DADE" stroke-width="3"/><circle cx="34" cy="30" r="3" fill="#D8DADE"/><circle cx="44" cy="30" r="3" fill="#D8DADE"/><path d="M40 46L54 54L40 62V46Z" fill="#E3E5E8"/></svg>' +
      '<div style="font-size:14px;color:#9B9B9B">还没有作品，去做第一条爆款视频吧</div>' +
      '<div class="btn-p" style="width:160px" data-go="home">去制作</div></div>';
    return;
  }
  box.innerHTML = '<div style="padding:20px">' + WORKS.map(function(w){
    return '<div class="wcard">' +
      '<div class="cov" style="background:linear-gradient(135deg,' + w.g[0] + ',' + w.g[1] + ')"><svg width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="11" fill="rgba(0,0,0,.28)"/><path d="M9.5 7.5L16 12L9.5 16.5V7.5Z" fill="#fff"/></svg></div>' +
      '<div class="txt"><b>' + w.n + '</b><span>' + w.t + '</span></div>' +
      '<div class="ops2" data-act="wops"><svg width="52" height="24" viewBox="0 0 52 24"><path d="M10 4V15M10 15L5.5 10.5M10 15L14.5 10.5" stroke="#5C5C5C" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 18V19C3 19.55 3.45 20 4 20H16C16.55 20 17 19.55 17 19V18" stroke="#5C5C5C" stroke-width="1.8" fill="none" stroke-linecap="round"/><path d="M35 6H49M39 6V4.5C39 4.22 39.22 4 39.5 4H44.5C44.78 4 45 4.22 45 4.5V6M36.5 6L37.4 18.5C37.43 18.78 37.66 19 37.94 19H46.06C46.34 19 46.57 18.78 46.6 18.5L47.5 6" stroke="#9B9B9B" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div>' +
    '</div>';
  }).join('') + '</div>';
}

/* ---------- 登录状态（移动端首页入口 + 桌面顶部导航入口） ---------- */
var logged = false;
function renderLoginEntry(){
  var html = logged
    ? '<div class="avatar" data-act="openMe">张</div>'
    : '<div class="login-btn" data-act="openLogin">登录</div>';
  $('#loginEntry').innerHTML = html;
  $('#loginEntryDesk').innerHTML = html;
}

/* ---------- 素材页状态 ---------- */
var hasImg = false;
function syncGenBtn(){
  var title = $('#i1').value.trim();
  $('#genBtn').disabled = !(hasImg && title.length > 0);
}
function bindCounters(){
  [['#i1','#c1',20],['#i2','#c2',30],['#i3','#c3',50]].forEach(function(x){
    var el = $(x[0]);
    function upd(){ $(x[1]).textContent = el.value.length + '/' + x[2]; syncGenBtn(); }
    el.addEventListener('input', upd);
    upd();
  });
}

/* ---------- 生成动画 ---------- */
var genTimer = null, leftGen = false;
var STEPS = ['解析模板','替换素材','生成视频','渲染输出'];
function startGen(){
  leftGen = false;
  var p = 0;
  clearInterval(genTimer);
  genTimer = setInterval(function(){
    p += 1.6;
    if(p > 100) p = 100;
    $('#pbar').style.width = p + '%';
    $('#pct').textContent = Math.round(p) + '%';
    var idx = Math.min(STEPS.length - 1, Math.floor(p / 25));
    $('#stepNow').textContent = '正在' + STEPS[idx];
    $('#stepsRow').innerHTML = STEPS.map(function(s, i){
      return i <= idx ? '<span class="done">' + s + '</span>' : '<span class="todo">' + s + '</span>';
    }).join('<span class="todo"> → </span>');
    if(p >= 100){
      clearInterval(genTimer);
      if(!leftGen){ stack = []; setTimeout(function(){ go('result') }, 500); }
    }
  }, 90);
}

/* ---------- 结果页播放条 ---------- */
var playTimer = null;
function startPlay(){
  clearInterval(playTimer);
  var w = 0;
  playTimer = setInterval(function(){
    w += 1; if(w > 100) w = 0;
    $('#vprog').style.width = w + '%';
  }, 150);
}

/* ---------- 动作分发 ---------- */
function act(name, el){
  switch(name){
    case 'openLogin':
      $('#m-login').style.display = 'flex';
      $('#m-confirm').style.display = 'none';
      $('#overlay').classList.add('on');
      break;
    case 'openMe':
      stack = []; go('me'); break;
    case 'doLogin':
      if($('#phone').value.length < 11){ toast('请输入 11 位手机号'); return; }
      logged = true; renderLoginEntry();
      $('#overlay').classList.remove('on');
      toast('登录成功，欢迎回来');
      break;
    case 'code':
      var b = $('#codeBtn'), n = 59;
      b.textContent = n + 's';
      b.style.pointerEvents = 'none';
      var iv = setInterval(function(){
        n--; b.textContent = n + 's';
        if(n <= 0){ clearInterval(iv); b.textContent = '获取验证码'; b.style.pointerEvents = 'auto'; }
      }, 1000);
      toast('验证码已发送（演示版：任意 4 位）');
      break;
    case 'kefu': toast('客服：工作日 9:00-21:00'); break;
    case 'seg':
      $$('.seg div').forEach(function(d){ d.classList.toggle('on', d === el) });
      var isTpl = el.getAttribute('data-v') === 'tpl';
      $('#tplPane').style.display = isTpl ? '' : 'none';
      $('#upPane').style.display = isTpl ? 'none' : '';
      break;
    case 'cat':
      curCat = el.getAttribute('data-v');
      renderCats(); renderGrid();
      break;
    case 'uploadRef':
      toast('视频上传中...');
      setTimeout(function(){ go('material') }, 900);
      break;
    case 'pickTpl':
      $('#mtName').textContent = el.getAttribute('data-v');
      $('#mtMeta').textContent = el.getAttribute('data-d');
      go('material');
      break;
    case 'upImg':
      hasImg = true;
      $('#thumb1').innerHTML = '<svg width="56" height="56" viewBox="0 0 56 56"><rect width="56" height="56" fill="#FFE3D9"/><circle cx="28" cy="22" r="10" fill="#FF9B78"/><path d="M8 52C8 38 17 32 28 32C39 32 48 38 48 52" fill="#FF9B78"/></svg>';
      el.textContent = '已上传';
      el.classList.add('gray');
      syncGenBtn();
      toast('产品图已上传');
      break;
    case 'upLogo': toast('Logo 已上传'); break;
    case 'toggle':
      var on = el.getAttribute('data-on') === '1';
      on = !on;
      el.setAttribute('data-on', on ? '1' : '0');
      el.innerHTML = on
        ? '<svg width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#FF4D1C"/><circle cx="32" cy="12" r="10" fill="#fff"/></svg>'
        : '<svg width="44" height="24" viewBox="0 0 44 24"><rect width="44" height="24" rx="12" fill="#DCDFE4"/><circle cx="12" cy="12" r="10" fill="#fff"/></svg>';
      break;
    case 'reset':
      hasImg = false;
      $('#thumb1').innerHTML = '<svg width="30" height="30" viewBox="0 0 30 30"><path d="M15 11V19M15 11L11.5 14.5M15 11L18.5 14.5" stroke="#B0B3B8" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/><path d="M9 21H21" stroke="#B0B3B8" stroke-width="1.8" fill="none" stroke-linecap="round"/></svg>';
      var ub = document.querySelector('[data-act="upImg"]');
      ub.textContent = '上传'; ub.classList.remove('gray');
      $('#i1').value = '全城最鲜火锅 开业5折';
      $('#i2').value = '招牌毛肚 8.8 元 进店就送';
      $('#i3').value = '欢迎来本店，开业期间全场5折，毛肚只要8块8，错过等一年！';
      bindCountersValues();
      syncGenBtn();
      toast('已恢复模板默认内容');
      break;
    case 'generate':
      if(!hasImg){ toast('请先上传产品图'); return; }
      if(!$('#i1').value.trim()){ toast('请填写视频大标题'); return; }
      $('#m-login').style.display = 'none';
      $('#m-confirm').style.display = 'flex';
      $('#overlay').classList.add('on');
      break;
    case 'closeConfirm':
      $('#overlay').classList.remove('on'); break;
    case 'doGenerate':
      $('#overlay').classList.remove('on');
      go('generating');
      break;
    case 'leaveGen':
      leftGen = true;
      stack = []; go('home', true);
      toast('已返回首页，生成完成后会通知你');
      break;
    case 'download': toast('已开始下载 · 无水印高清版'); break;
    case 'share': toast('链接已复制，去发给好友吧'); break;
    case 'regen': toast('已重新生成'); go('generating'); break;
    case 'play': toast('播放 / 暂停'); break;
    case 'pickAvatar': toast('功能开发中'); break;
    case 'filter': toast('筛选功能演示版未开放'); break;
    case 'wops': toast('下载 / 删除'); break;
    case 'balance': toast('剩余 3 次免费额度'); break;
    case 'setting': toast('设置页演示版未开放'); break;
    case 'logout':
      logged = false; renderLoginEntry();
      stack = []; go('home', true);
      toast('已退出登录');
      break;
  }
}
function bindCountersValues(){
  [['#i1','#c1',20],['#i2','#c2',30],['#i3','#c3',50]].forEach(function(x){
    $(x[1]).textContent = $(x[0]).value.length + '/' + x[2];
  });
}

/* ---------- 点击遮罩关闭 ---------- */
$('#overlay').addEventListener('click', function(e){
  if(e.target === this) this.classList.remove('on');
});

/* ---------- 原型演示:拖拽视频到上传区(模拟上传流程) ---------- */
(function(){
  var zone = document.querySelector('#upPane .upload-zone');
  if(!zone) return;
  ['dragenter','dragover'].forEach(function(ev){
    zone.addEventListener(ev, function(e){ e.preventDefault(); zone.classList.add('dragover'); });
  });
  ['dragleave','drop'].forEach(function(ev){
    zone.addEventListener(ev, function(e){ e.preventDefault(); zone.classList.remove('dragover'); });
  });
  zone.addEventListener('drop', function(e){
    var file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
    if(file && file.type && file.type.indexOf('video/') !== 0){ toast('请拖入视频文件'); return; }
    toast('视频上传中...');
    setTimeout(function(){ go('material') }, 900);
  });
})();

/* ---------- 初始化 ---------- */
renderCats(); renderGrid(); renderAvatars(); renderWorks(); renderLoginEntry(); bindCounters(); syncTopnav();
