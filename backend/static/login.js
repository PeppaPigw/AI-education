const inputs = document.querySelectorAll(".input-field");
const toggle_btn = document.querySelectorAll(".toggle");
const main = document.querySelector("main");
const bullets = document.querySelectorAll(".bullets span");
const images = document.querySelectorAll(".image");

inputs.forEach((inp) => {
  inp.addEventListener("focus", () => {
    inp.classList.add("active");
  });
  inp.addEventListener("blur", () => {
    if (inp.value != "") return;
    inp.classList.remove("active");
  });
});

toggle_btn.forEach((btn) => {
  btn.addEventListener("click", () => {
    main.classList.toggle("sign-up-mode");
  });
});

function moveSlider() {
  let index = this.dataset.value;

  let currentImage = document.querySelector(`.img-${index}`);
  images.forEach((img) => img.classList.remove("show"));
  currentImage.classList.add("show");

  const textSlider = document.querySelector(".text-group");
  textSlider.style.transform = `translateY(${-(index - 1) * 2.2}rem)`;

  bullets.forEach((bull) => bull.classList.remove("active"));
  this.classList.add("active");
}

bullets.forEach((bullet) => {
  bullet.addEventListener("click", moveSlider);
});

const signInForm = document.querySelector(".sign-in-form");
const signUpForm = document.querySelector(".sign-up-form");

function handleLogin(event) {
  event.preventDefault(); 

  const form = event.currentTarget;
  const inputs = form.querySelectorAll(".input-field");
  const username = inputs[0].value.trim();
  const password = inputs[1].value.trim();

  fetch("/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
    .then((response) => {
      if (!response.ok) {
        // 如果状态码不是 2xx (如 401)，抛出错误
        return response.json().then((err) => {
          throw new Error(err.detail || "Login failed");
        });
      }
      return response.json();
    })
    .then((data) => {
      // 登录成功，跳转到 /index.html
      window.location.href = data.redirect_url;
    })
    .catch((error) => {
      // 登录失败，显示错误信息
      alert(`登录失败: ${error.message}`);
    });
}

// 绑定事件
if (signInForm) signInForm.addEventListener("submit", handleLogin);
if (signUpForm) signUpForm.addEventListener("submit", handleLogin);
