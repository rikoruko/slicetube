const $=id=>document.getElementById(id);
let videoDuration=0, format="mp4", quality="best";
function time(v){v=Math.max(0,Math.floor(Number(v)||0));return `${Math.floor(v/60)}:${String(v%60).padStart(2,"0")}`}
function status(msg,error=false){$("status").textContent=msg;$("status").className="status"+(error?" error":"")}
$("load").onclick=async()=>{
 const url=$("url").value.trim();if(!url)return status("Paste a YouTube URL first.",true);
 $("load").disabled=true;status("Loading video details…");
 try{const r=await fetch("/api/info",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url})});const d=await r.json();if(!r.ok)throw Error(d.error);
 videoDuration=d.duration||0;$("title").textContent=d.title;$("thumb").src=d.thumbnail;$("duration").textContent=`Duration: ${time(videoDuration)}`;
 $("start").max=videoDuration;$("end").max=videoDuration;$("end").value=Math.min(30,videoDuration||30);
 $("rangeStart").max=videoDuration;$("rangeEnd").max=videoDuration;$("rangeEnd").value=$("end").value;
 $("editor").hidden=false;status("Video ready. Set your clip range below.");
 }catch(e){status(e.message,true)}finally{$("load").disabled=false}
};
function sync(){let s=+$("start").value,e=+$("end").value;$("rangeStart").value=s;$("rangeEnd").value=e;$("selected").textContent=`${time(Math.max(0,e-s))} selected`}
$("start").oninput=sync;$("end").oninput=sync;
$("rangeStart").oninput=()=>{$("start").value=$("rangeStart").value;sync()};
$("rangeEnd").oninput=()=>{$("end").value=$("rangeEnd").value;sync()};
document.querySelectorAll("#formats .choice").forEach(b=>b.onclick=()=>{format=b.dataset.value;document.querySelectorAll("#formats .choice").forEach(x=>x.classList.toggle("active",x===b))});
document.querySelectorAll("#qualities .choice").forEach(b=>b.onclick=()=>{quality=b.dataset.value;document.querySelectorAll("#qualities .choice").forEach(x=>x.classList.toggle("active",x===b))});
$("export").onclick=async()=>{
 if(!$("authorized").checked)return status("Confirm that you own or have permission to use this video.",true);
 const s=+$("start").value,e=+$("end").value;if(e<=s)return status("End time must be after start time.",true);
 $("export").disabled=true;$("export").textContent="Preparing your clip…";status("Processing can take a few minutes. Keep this tab open.");
 try{const r=await fetch("/api/clip",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:$("url").value,start:s,end:e,quality,format,authorized:true})});
 if(!r.ok){const d=await r.json();throw Error(d.error||"Export failed")}
 const blob=await r.blob(),a=document.createElement("a"),u=URL.createObjectURL(blob);a.href=u;a.download=`slicefree-clip.${format}`;a.click();URL.revokeObjectURL(u);status("Your clip is ready.");
 }catch(e){status(e.message,true)}finally{$("export").disabled=false;$("export").innerHTML='Export clip <span>↗</span>'}
};
