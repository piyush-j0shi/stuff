var toast = document.getElementById('toast');
if (toast) {
  setTimeout(function () { toast.classList.add('show'); }, 30);
  setTimeout(function () { toast.classList.remove('show'); }, 3200);
}
