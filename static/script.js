document.addEventListener("DOMContentLoaded", () => {

  /**********************
   * LOGIN FUNCTIONALITY *
   **********************/
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const email = document.getElementById("username").value.trim();
      const password = document.getElementById("password").value;

      const users = JSON.parse(localStorage.getItem("users") || "[]");
      const user = users.find(u => u.email === email && u.password === password);

      if (user) {
        if (user.role.toLowerCase() === "employer") {
          window.location.href = "employer-dashboard.html";
        } else {
          window.location.href = "user-dashboard.html";
        }
      } else {
        alert("Invalid credentials. Please try again.");
      }
    });

    const registerBtn = document.getElementById("registerBtn");
    if (registerBtn) {
      registerBtn.addEventListener("click", () => {
        window.location.href = "register.html";
      });
    }
  }

  /*********************************
   * EMPLOYER LOGIN FUNCTIONALITY  *
   *********************************/
  const employerLoginForm = document.getElementById("employerLoginForm");
  if (employerLoginForm) {
    employerLoginForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const email = document.getElementById("empUsername").value.trim();
      const password = document.getElementById("empPassword").value;

      const users = JSON.parse(localStorage.getItem("users") || "[]");
      const user = users.find(u => u.email === email && u.password === password && u.role.toLowerCase() === "employer");

      if (user) {
        window.location.href = "employer-dashboard.html";
      } else {
        alert("Invalid employer credentials. Please try again.");
      }
    });
  }

  /********************************
   * REGISTRATION FUNCTIONALITY    *
   ********************************/
  const registerForm = document.getElementById("registerForm");
  if (registerForm) {
    registerForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const fullName = document.getElementById("fullName").value.trim();
      const email = document.getElementById("regEmail").value.trim();
      const password = document.getElementById("password").value;
      const role = document.getElementById("role").value;

      let users = JSON.parse(localStorage.getItem("users")) || [];
      if (users.some(u => u.email === email)) {
        alert("Email already registered.");
        return;
      }

      users.push({ fullName, email, password, role });
      localStorage.setItem("users", JSON.stringify(users));
      alert("Registration successful! Redirecting to login...");
      window.location.href = "login.html";
    });
  }

  /*******************************
   * LOGOUT FUNCTIONALITY *
   *******************************/
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      window.location.href = "login.html";
    });
  }

  /***********************************
   * USER DASHBOARD FUNCTIONALITY    *
   ***********************************/
  const resumeUploadForm = document.getElementById("resumeUploadForm");

  if (resumeUploadForm) {
    resumeUploadForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const resumeFile = document.getElementById("resume").files[0];
      const jobDescriptionFile = document.getElementById("jobDescription").files[0];

      if (!resumeFile || !jobDescriptionFile) {
        alert("Please select both files.");
        return;
      }

      alert("Files ready to upload and compare.");
    });
  }

});
