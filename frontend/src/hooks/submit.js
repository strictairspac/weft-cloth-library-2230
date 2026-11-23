export function submit(id, action, fail, done=()=>{}) {
  document.getElementById(id)?.addEventListener('submit', async event=>{
    event.preventDefault();
    const button = event.submitter;
    if (button) button.disabled = true;
    try { await action(new FormData(event.currentTarget)); done(); }
    catch (error) { fail(error); }
    finally { if (button) button.disabled = false; }
  });
}
