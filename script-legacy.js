<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#174c35"><title>Gohar — AI Kheti Salahkar</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="brand"><div class="brand-icon">🌾</div><div><strong>गोहर <span>GOHAR</span></strong><small>AI Kheti Salahkar</small></div></div>
    <p class="label">YOUR FARMING ASSISTANT</p>
    <button id="newChat" class="new-chat">＋ &nbsp; New conversation</button>
    <div class="side-note"><div>🌱</div><b>Apni bhasha mein</b><p>Simple farming guidance in Hindi and Awadhi.</p></div>
    <div class="side-bottom"><span class="dot"></span> Open-source project<p>Built for farmers near Lucknow, Uttar Pradesh.</p></div>
  </aside>
  <main>
    <header class="topbar"><div class="mobile-brand">🌾 <b>गोहर GOHAR</b></div><span class="status"><i class="dot"></i> Prototype demo</span></header>
    <section id="welcome" class="welcome">
      <div class="eyebrow">✦ &nbsp; KISANO KE LIYE, KISANO KI BHASHA MEIN</div>
      <h1>Namaste, <em>kisan bhai!</em></h1>
      <p class="intro">Aaj khet mein kya dikkat hai? Apna sawal poochhiye.<br>Gohar aapko kheti ki jaankari samajhne mein madad karega.</p>
      <div class="cards">
        <button class="topic" data-prompt="Gehu ke patte peele pad rahe hain, kya karun?"><span class="emoji wheat">🌾</span><span><b>Fasal ki dikkat</b><small>Patte peele ya growth kam</small></span><span class="arrow">↗</span></button>
        <button class="topic" data-prompt="Gehu mein khaad kab aur kaise deni chahiye?"><span class="emoji green">🌱</span><span><b>Khaad ki salah</b><small>Timing aur crop stage</small></span><span class="arrow">↗</span></button>
        <button class="topic" data-prompt="Mere khet ke liye mausam ki jaankari kaise check karun?"><span class="emoji blue">☁️</span><span><b>Mausam ki jaankari</b><small>Baarish aur savdhani</small></span><span class="arrow">↗</span></button>
        <button class="topic" data-prompt="Sarson ki fasal mein keede dikh rahe hain, kya check karun?"><span class="emoji orange">🐛</span><span><b>Keede aur rog</b><small>Possible cause aur next steps</small></span><span class="arrow">↗</span></button>
      </div>
    </section>
    <section id="conversation" class="conversation hidden" aria-live="polite"></section>
    <section class="composer-wrap">
      <form id="chatForm" class="composer">
        <textarea id="question" rows="1" placeholder="Apna sawal yahan likhein..." aria-label="Farming question"></textarea>
        <div class="composer-foot"><span>✦ Hindi ya Awadhi mein poochhein</span><button type="submit" aria-label="Send question">↑</button></div>
      </form>
      <p class="disclaimer">Demo prototype: advice can be incomplete. Verify important farming decisions with a local agricultural expert.</p>
    </section>
  </main>
</div>
<script src="script.js"></script>
</body></html>