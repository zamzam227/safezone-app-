
const ST=["Pengaduan Diterima","Menunggu Peninjauan","Sedang Ditinjau","Tindak Lanjut","Pemantauan","Selesai Ditangani"];
const IC=["📩","⏳","🔎","🤝","👀","✅"];
const DS=["Laporanmu sudah masuk dan tercatat dengan aman.","Laporan menunggu giliran dibaca oleh petugas sekolah.","Petugas sedang membaca dan memeriksa laporanmu.","Petugas melakukan langkah bantuan, misalnya bicara dengan pihak terkait.","Petugas memantau agar kejadian tidak terulang.","Kasus sudah ditangani. Kamu tetap bisa melapor lagi kapan saja."];
const api=async(m,u,b)=>{const r=await fetch(u,{method:m,headers:{"Content-Type":"application/json","X-Requested-With":"fetch"},body:b?JSON.stringify(b):undefined});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||"Terjadi kesalahan.");return d};
const $=s=>document.querySelector(s),esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=t=>new Date(t).toLocaleString("id-ID",{day:"numeric",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit"});
let U=null,V="home",flash="";
let D={reports:[],log:[],jurnal:[],staff:[]};
async function sync(){if(!U)return;D.reports=(await api("GET","/api/reports")).reports;if(U.role=="siswa")D.jurnal=(await api("GET","/api/journal")).items;else{D.staff=(await api("GET","/api/staff")).staff;if(V=="log")D.log=(await api("GET","/api/activity")).items}}
async function refresh(){try{await sync()}catch(e){flash=esc(e.message)}render()}
async function go(v){V=v;await refresh();scrollTo(0,0)}
function render(){
 const nav=$("#nav");let items=[];
 if(!U)items=[["home","Beranda"],["login","Masuk"]];
 else if(U.role=="siswa")items=[["home","Beranda"],["lapor","Lapor"],["lacak","Lacak"],["jurnal","Jurnal"],["edu","Edukasi"],["kontak","Kontak"]];
 else items=[["dash","Dashboard"],["log","Riwayat aktivitas"]];
 nav.innerHTML=items.map(([k,l])=>`<button class="${V==k?"on":""}" data-v="${k}" ${V==k?'aria-current="page"':""}>${l}</button>`).join("");
 nav.querySelectorAll("button").forEach(b=>b.onclick=()=>go(b.dataset.v));
 $("#who").innerHTML=U?`<span class="tm">${esc(U.name)}</span><button class="tab" id="out">Keluar</button>`:"";
 if(U)$("#out").onclick=async()=>{await api("POST","/api/logout");U=null;D.reports=[];go("home")};
 if(U&&U.role!="siswa"&&!["dash","log","det"].includes(V))V="dash";
 if(U&&U.role=="siswa"&&["dash","log","det"].includes(V))V="home";
 if(!U&&!["home","login"].includes(V))V="login";
 $("#m").innerHTML=(flash?`<div class="note" role="status">${flash}</div>`:"")+(VIEWS[V]?VIEWS[V]():"");flash="";
 (BIND[V]||(()=>{}))();
}
function tl(r,open){
 const done=r.st,pct=Math.round((done+1)/6*100);
 return `<div class="bar" role="progressbar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><i style="width:${pct}%"></i></div><ol class="tl">${ST.map((s,i)=>{
  const h=r.hist.find(x=>x.s==i),cls=i<done?"d":i==done?"c":"f";
  const show=open||i==done;
  return `<li class="${cls}"><div class="dot" aria-hidden="true">${IC[i]}</div><div><strong>${s}</strong>${i==done?' <span class="pill">Saat ini</span>':""}<div class="tm">${h?fmt(h.t):"Belum dimulai"}</div>${show&&h?`<div>${DS[i]}${h.n?`<br><em>Catatan petugas: ${esc(h.n)}</em>`:""}</div>`:""}</div></li>`}).join("")}</ol>`}
const mine=()=>D.reports;
const VIEWS={
home:()=>`<section class="hero"><h1>Suara Aman, Masa Depan Nyaman.</h1><p>Tempat aman bagi siswa SD untuk melapor cyberbullying, memantau penanganannya, dan mendapat dukungan.</p>${U?`<button class="btn" data-v="lapor">Buat pengaduan</button>`:`<button class="btn" data-v="login">Masuk untuk mulai</button>`}</section>
 <div class="grid">${[["🛡️","Lapor dengan aman","Identitasmu bisa disembunyikan dari teman."],["🔎","Pantau prosesnya","Lihat status laporan seperti melacak paket."],["💙","Dukungan emosi","Jurnal perasaan dan latihan napas."],["👩‍🏫","Orang dewasa tepercaya","Hubungi guru BK kapan saja."]].map(c=>`<div class="card"><div style="font-size:2rem">${c[0]}</div><h3>${c[1]}</h3><p>${c[2]}</p></div>`).join("")}</div>
 ${U&&U.role=="siswa"?`<div class="card"><h2>Halo, ${esc(U.name)}</h2><p>Kamu punya ${mine().length} pengaduan.</p></div>`:""}`,
login:()=>`<div class="card"><h2 id="lt">Masuk</h2><form id="lf" novalidate><label for="un">Nama pengguna</label><input id="un" autocomplete="username"><label for="nm" id="nml" hidden>Nama panggilan</label><input id="nm" hidden><label for="pw">Kata sandi</label><input id="pw" type="password" autocomplete="current-password"><div class="err" id="le" role="alert"></div><div class="row"><button class="btn" type="submit" id="lb">Masuk</button><button class="btn g" type="button" id="lr">Belum punya akun? Daftar</button></div></form><p class="note">Akun petugas dibuat oleh koordinator sekolah. Kata sandi minimal 8 karakter.</p></div>`,
lapor:()=>`<div class="card"><h2>Form pengaduan</h2><form id="f" novalidate>
 <label for="k">Jenis kejadian</label><select id="k"><option value="">Pilih...</option><option>Pesan kasar</option><option>Penyebaran foto</option><option>Akun palsu</option><option>Dikucilkan online</option><option>Lainnya</option></select>
 <label for="p">Di mana kejadiannya?</label><input id="p" placeholder="Contoh: grup WhatsApp, game online">
 <label for="d">Ceritakan apa yang terjadi</label><textarea id="d" rows="5" placeholder="Minimal 20 huruf"></textarea>
 <label for="b">Bukti (opsional, PNG/JPG/PDF maks. 2 MB)</label><input id="b" type="file" accept="image/png,image/jpeg,application/pdf">
 <label><input type="checkbox" id="a" style="width:auto"> Sembunyikan namaku dari tampilan petugas</label>
 <div class="err" id="e" role="alert"></div><button class="btn" type="submit">Kirim pengaduan</button></form>
 <p class="note">Bukti disimpan di server dan hanya bisa dibuka olehmu dan petugas yang menangani.</p></div>`,
lacak:()=>`<div class="card"><h2>Lacak pengaduan</h2><div class="row"><input id="q" placeholder="Nomor referensi, mis. SZ-DEMO-0001" style="flex:1;min-width:200px"><button class="btn s" id="qb">Cari</button></div><div class="err" id="qe" role="alert"></div></div>
 ${mine().map(r=>`<div class="card"><div class="row"><h3 style="flex:1">${r.ref}</h3><span class="pill">${ST[r.st]}</span></div><p>${esc(r.kat)} · ${esc(r.plat)}</p>${tl(r,open[r.ref])}<button class="btn g" data-t="${r.ref}">${open[r.ref]?"Ringkas riwayat":"Perluas riwayat"}</button></div>`).join("")||'<div class="card">Belum ada pengaduan. Buat yang pertama lewat menu Lapor.</div>'}`,
jurnal:()=>{const j=D.jurnal;return `<div class="card"><h2>Jurnal emosi</h2><div class="moods" id="mo">${["😊","😐","😢","😠","😨"].map(e=>`<button data-e="${e}" aria-label="Perasaan ${e}">${e}</button>`).join("")}</div><textarea id="jn" rows="3" placeholder="Apa yang kamu rasakan hari ini?"></textarea><div class="err" id="je"></div><button class="btn" id="js">Simpan jurnal</button>${j.map(x=>`<p><strong>${x.e}</strong> <span class="tm">${fmt(x.t)}</span><br>${esc(x.n)}</p>`).join("")}</div>
 <div class="card"><h2>Latihan napas</h2><p>Tarik napas, tahan, lalu hembuskan pelan.</p><div id="br">Mulai</div><div class="row" style="justify-content:center"><button class="btn s" id="bs">Mulai latihan</button></div></div>`},
edu:()=>`<div class="card"><h2>Edukasi keamanan digital</h2>${[["Apa itu cyberbullying?","Perilaku menyakiti orang lain lewat internet, seperti mengejek, mengancam, atau menyebar foto tanpa izin."],["Kalau ada yang mengejekku online","Jangan membalas. Simpan bukti (tangkapan layar), lalu ceritakan ke orang dewasa tepercaya."],["Jaga kata sandi","Jangan bagikan kata sandi, bahkan ke teman dekat. Gunakan kata sandi yang sulit ditebak."],["Sebelum membagikan foto","Tanyakan: apakah orang di foto ini setuju? Jika ragu, jangan kirim."]].map(a=>`<details><summary>${a[0]}</summary><p>${a[1]}</p></details>`).join("")}</div>`,
kontak:()=>`<div class="card"><h2>Orang dewasa tepercaya</h2><div class="grid"><div class="card"><h3>👩‍🏫 Guru BK sekolah</h3><p>Datang ke ruang BK atau minta wali kelas mengantarmu.</p></div><div class="card"><h3>📞 SAPA 129</h3><p>Layanan pengaduan kekerasan terhadap anak dari Kementerian PPPA. Hubungi 129.</p></div><div class="card"><h3>🏠 Orang tua / wali</h3><p>Ceritakan apa yang kamu alami. Kamu tidak salah.</p></div></div></div>`,
dash:()=>{const fs=$("#fs")?$("#fs").value:"",fk=$("#fk")?$("#fk").value:"";const L=D.reports.filter(r=>(fs===""||r.st==fs)&&(!fk||r.kat==fk));
 return `<div class="card"><h2>Daftar pengaduan</h2><div class="row"><select id="fs" style="width:auto"><option value="">Semua status</option>${ST.map((s,i)=>`<option value="${i}" ${fs==i&&fs!==""?"selected":""}>${s}</option>`).join("")}</select><select id="fk" style="width:auto"><option value="">Semua kategori</option>${["Pesan kasar","Penyebaran foto","Akun palsu","Dikucilkan online","Lainnya"].map(k=>`<option ${fk==k?"selected":""}>${k}</option>`).join("")}</select></div>
 <div class="scroll"><table><tr><th>Referensi</th><th>Kategori</th><th>Status</th><th>Petugas</th><th></th></tr>${L.map(r=>`<tr><td>${r.ref}</td><td>${esc(r.kat)}</td><td><span class="pill">${ST[r.st]}</span></td><td>${esc(r.assign)||"-"}</td><td><button class="btn s" data-d="${r.ref}">Buka</button></td></tr>`).join("")||"<tr><td colspan=5>Tidak ada laporan.</td></tr>"}</table></div></div>`},
det:()=>{const r=D.reports.find(x=>x.ref==cur);return `<div class="card"><button class="btn g" data-v="dash">Kembali</button><h2>${r.ref}</h2><p><strong>${esc(r.kat)}</strong> di ${esc(r.plat)}<br>Pelapor: ${esc(r.pelapor)}<br>Bukti: ${r.hasFile?`<a href="/api/reports/${r.ref}/file" target="_blank" rel="noopener">${esc(r.bukti[0])}</a>`:"-"}</p><p>${esc(r.desc)}</p>
 <div class="row"><label for="as" style="margin:0">Petugas:</label><select id="as" style="width:auto"><option value="">Belum ditugaskan</option>${(U.role=="admin"?D.staff:[{id:U.id,name:U.name}]).map(s=>`<option value="${s.id}" ${r.assignId==s.id?"selected":""}>${esc(s.name)}</option>`).join("")}</select></div>
 <label for="nt">Catatan tindak lanjut</label><textarea id="nt" rows="2"></textarea><div class="err" id="ne"></div>
 <div class="row">${r.st<5?`<button class="btn" id="adv">Majukan ke: ${ST[r.st+1]}</button>`:"<span class='pill'>Selesai</span>"}<button class="btn s" id="addn">Simpan catatan</button></div>
 ${r.notes.length?`<h3 style="margin-top:14px">Catatan</h3>${r.notes.map(n=>`<p class="tm">${fmt(n.t)} · ${esc(n.by)}<br><span style="color:var(--tx)">${esc(n.n)}</span></p>`).join("")}`:""}</div><div class="card"><h3>Timeline</h3>${tl(r,true)}</div>`},
log:()=>`<div class="card"><h2>Riwayat aktivitas</h2>${D.log.map(l=>`<p><span class="tm">${fmt(l.t)} · ${esc(l.by)}</span><br>${esc(l.a)}</p>`).join("")||"Belum ada aktivitas."}</div>`};
let cur="",open={};
const BIND={
login:()=>{let reg=false;$("#lr").onclick=()=>{reg=!reg;$("#nm").hidden=$("#nml").hidden=!reg;$("#lt").textContent=reg?"Buat akun siswa":"Masuk";$("#lb").textContent=reg?"Daftar":"Masuk";$("#lr").textContent=reg?"Sudah punya akun? Masuk":"Belum punya akun? Daftar"};
 $("#lf").onsubmit=async e=>{e.preventDefault();try{const b={username:$("#un").value.trim(),password:$("#pw").value};if(reg)b.name=$("#nm").value.trim();U=(await api("POST",reg?"/api/register":"/api/login",b)).user;go(U.role=="siswa"?"home":"dash")}catch(x){$("#le").textContent=x.message}}},
lapor:()=>{$("#f").onsubmit=async e=>{e.preventDefault();const k=$("#k").value,p=$("#p").value.trim(),d=$("#d").value.trim(),f=$("#b").files[0],er=$("#e");
 if(!k)return er.textContent="Pilih jenis kejadian.";if(!p)return er.textContent="Tulis di mana kejadiannya.";if(d.length<20)return er.textContent="Ceritanya minimal 20 huruf.";
 if(f&&f.size>2097152)return er.textContent="Berkas bukti maksimal 2 MB.";
 try{let file=null;if(f)file=await new Promise((ok,no)=>{const r=new FileReader();r.onload=()=>ok({name:f.name,data:r.result.split(",")[1]});r.onerror=no;r.readAsDataURL(f)});
 const r=await api("POST","/api/reports",{kat:k,plat:p,desc:d,anon:$("#a").checked,file});flash=`Pengaduan terkirim. Simpan nomor referensimu: <strong>${r.ref}</strong>`;go("lacak")}catch(x){er.textContent=x.message}}},
lacak:()=>{$("#qb").onclick=()=>{const q=$("#q").value.trim().toUpperCase();if(!q)return;const r=mine().find(x=>x.ref==q);$("#qe").textContent=r?"":"Nomor tidak ditemukan di pengaduanmu.";if(r){open[r.ref]=true;render();document.querySelector(`[data-t="${r.ref}"]`).scrollIntoView()}};
 document.querySelectorAll("[data-t]").forEach(b=>b.onclick=()=>{open[b.dataset.t]=!open[b.dataset.t];render()})},
jurnal:()=>{let em="";document.querySelectorAll("#mo button").forEach(b=>b.onclick=()=>{em=b.dataset.e;document.querySelectorAll("#mo button").forEach(x=>x.classList.toggle("on",x==b))});
 $("#js").onclick=async()=>{const n=$("#jn").value.trim();if(!em||!n)return $("#je").textContent="Pilih perasaan dan tulis sedikit cerita.";try{await api("POST","/api/journal",{e:em,n});await refresh()}catch(x){$("#je").textContent=x.message}};
 let iv;$("#bs").onclick=()=>{clearInterval(iv);const el=$("#br");const ph=[["Tarik napas",4],["Tahan",4],["Hembuskan",6]];let i=0,c=0;const step=()=>{const [l,s]=ph[i%3];el.textContent=l;el.style.transitionDuration=s+"s";el.style.transform=l=="Tarik napas"?"scale(1.4)":l=="Hembuskan"?"scale(1)":el.style.transform;setTimeout(()=>{if(++c<9&&document.body.contains(el)){i++;step()}else el.textContent="Bagus!"},s*1e3)};step()}},
dash:()=>{["fs","fk"].forEach(i=>$("#"+i).onchange=render);document.querySelectorAll("[data-d]").forEach(b=>b.onclick=()=>{cur=b.dataset.d;go("det")})},
det:()=>{const r=D.reports.find(x=>x.ref==cur),P=async(u,b)=>{try{await api("POST","/api/reports/"+r.ref+u,b);await refresh()}catch(x){flash=esc(x.message);await refresh()}};
 $("#as").onchange=e=>P("/assign",{uid:e.target.value||null});
 $("#addn").onclick=()=>P("/notes",{n:$("#nt").value.trim()});
 const a=$("#adv");if(a)a.onclick=()=>P("/advance",{n:$("#nt").value.trim()})}};
document.addEventListener("click",e=>{const b=e.target.closest("[data-v]");if(b&&!b.closest("nav"))go(b.dataset.v)});
$("#lg").onclick=()=>go(U&&U.role!="siswa"?"dash":"home");
(async()=>{try{U=(await api("GET","/api/me")).user}catch(e){}V=U?(U.role=="siswa"?"home":"dash"):"home";await refresh()})();
