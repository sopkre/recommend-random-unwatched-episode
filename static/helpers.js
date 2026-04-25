

// To hide and reveal content with button 
function readMoreReadLess(id) {
  var dots = document.getElementById("dots_" + id);
  var moreText = document.getElementById("more_" + id);
  var btnText = document.getElementById("myBtn_" + id);

  if (dots.style.display === "none") {
    dots.style.display = "inline";
    btnText.innerHTML = "↓ Show";
    moreText.style.display = "none";
  } else {
    dots.style.display = "none";
    btnText.innerHTML = "↑ Hide";
    moreText.style.display = "inline";
  }
} 


// To open and close dialog window
function handleDialog(id, event) {
    element = document.getElementById(id); 
    if (event == 'close'){
        element.close();
    } else if (event == 'open') {
        element.showModal();
    } else {
        pass;
    }
}