import {topic} from '../constants/project.js';
import {esc} from '../utils/dom.js';

export function loginPage() {
  return `<main class="login"><section class="login-story">
    <p class="kicker">${esc(topic.direction)}</p><h1>${esc(topic.name)}</h1><p class="lede">${esc(topic.algorithm)}</p>
    <ol>${topic.modules.map(x=>`<li>${esc(x)}</li>`).join('')}</ol></section>
    <section class="login-form"><h2>登录</h2><div id="message" role="alert"></div>
    <form id="login-form"><label>账号<input name="username" autocomplete="username" value="operator" required></label>
    <label>密码<input name="password" type="password" autocomplete="current-password" required></label>
    <button>进入工作台</button></form><p class="note">经办员 operator · 复核员 reviewer · 观察员 viewer</p>
    <p class="note">演示密码 <code>Demo-Walkthrough-2026</code></p></section></main>`;
}
