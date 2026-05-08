document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const authForm = document.getElementById("auth-form");
  const authStatus = document.getElementById("auth-status");
  const logoutButton = document.getElementById("logout-button");
  const emailInput = document.getElementById("email");
  const signupHelp = document.getElementById("signup-help");

  let currentUser = null;

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function renderAuthState(session) {
    currentUser = session.user;
    const authenticated = session.authenticated;

    authStatus.className = authenticated ? "auth-status success" : "auth-status info";
    authStatus.textContent = authenticated
      ? `Signed in as ${currentUser.username} (${currentUser.role})`
      : "Viewing as guest. Log in to manage registrations.";

    authForm.classList.toggle("hidden", authenticated);
    logoutButton.classList.toggle("hidden", !authenticated);

    emailInput.disabled = !authenticated;
    activitySelect.disabled = !authenticated;
    signupForm.querySelector("button").disabled = !authenticated;

    if (!authenticated) {
      emailInput.value = "";
      emailInput.readOnly = false;
      signupHelp.textContent =
        "Log in to sign up. Students can register only themselves, while admins can register or remove any student.";
      return;
    }

    if (currentUser.role === "student") {
      emailInput.value = currentUser.email;
      emailInput.readOnly = true;
      signupHelp.textContent = "Student mode: you can register only your own email address.";
      return;
    }

    emailInput.readOnly = false;
    emailInput.value = "";
    signupHelp.textContent = "Admin mode: you can register or remove any student.";
  }

  async function loadSession() {
    const response = await fetch("/auth/session");
    const session = await response.json();
    renderAuthState(session);
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${
                        currentUser && currentUser.role === "admin"
                          ? `<button class="delete-btn" data-activity="${name}" data-email="${email}">Remove</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      });

      const result = await response.json();

      if (!response.ok) {
        showMessage(result.detail || "Login failed.", "error");
        return;
      }

      authForm.reset();
      renderAuthState(result);
      showMessage(`Logged in as ${result.user.username}.`, "success");
      fetchActivities();
    } catch (error) {
      showMessage("Failed to log in. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  }

  async function handleLogout() {
    try {
      await fetch("/auth/logout", { method: "POST" });
      renderAuthState({ authenticated: false, user: null });
      showMessage("Logged out.", "success");
      fetchActivities();
    } catch (error) {
      showMessage("Failed to log out. Please try again.", "error");
      console.error("Error logging out:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();

        if (currentUser && currentUser.role === "student") {
          emailInput.value = currentUser.email;
        }

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  authForm.addEventListener("submit", handleLogin);
  logoutButton.addEventListener("click", handleLogout);

  // Initialize app
  loadSession()
    .catch((error) => {
      console.error("Error loading session:", error);
      renderAuthState({ authenticated: false, user: null });
    })
    .finally(fetchActivities);
});
