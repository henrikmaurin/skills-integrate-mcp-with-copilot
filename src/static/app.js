document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginToggle = document.getElementById("login-toggle");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("logout-button");
  const signupContainer = document.getElementById("signup-container");
  const userMenuLabel = document.getElementById("user-menu-label");
  const teacherStatus = document.getElementById("teacher-status");
  let isTeacher = false;

  function showMessage(message, type) {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");

    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }

  function updateAuthControls(username) {
    isTeacher = Boolean(username);
    signupContainer.classList.toggle("hidden", !isTeacher);
    loginToggle.classList.toggle("hidden", isTeacher);
    loginForm.classList.add("hidden");
    loginToggle.setAttribute("aria-expanded", "false");
    logoutButton.classList.toggle("hidden", !isTeacher);
    teacherStatus.classList.toggle("hidden", !isTeacher);
    teacherStatus.textContent = isTeacher ? `Signed in: ${username}` : "";
    userMenuLabel.textContent = "Teacher login";
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error(`Activity request failed with status ${response.status}`);
      }
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;
        const title = document.createElement("h4");
        title.textContent = name;
        activityCard.appendChild(title);

        const description = document.createElement("p");
        description.textContent = details.description;
        activityCard.appendChild(description);

        const schedule = document.createElement("p");
        const scheduleLabel = document.createElement("strong");
        scheduleLabel.textContent = "Schedule:";
        schedule.append(scheduleLabel, ` ${details.schedule}`);
        activityCard.appendChild(schedule);

        const availability = document.createElement("p");
        const availabilityLabel = document.createElement("strong");
        availabilityLabel.textContent = "Availability:";
        availability.append(availabilityLabel, ` ${spotsLeft} spots left`);
        activityCard.appendChild(availability);

        const participantsContainer = document.createElement("div");
        participantsContainer.className = "participants-container";
        const participantsSection = document.createElement("div");
        participantsSection.className = "participants-section";
        const participantsHeading = document.createElement("h5");
        participantsHeading.textContent = "Participants:";
        participantsSection.appendChild(participantsHeading);

        if (details.participants.length > 0) {
          const participantsList = document.createElement("ul");
          participantsList.className = "participants-list";

          details.participants.forEach((email) => {
            const participantItem = document.createElement("li");
            const participantEmail = document.createElement("span");
            participantEmail.className = "participant-email";
            participantEmail.textContent = email;
            participantItem.appendChild(participantEmail);

            if (isTeacher) {
              const removeButton = document.createElement("button");
              removeButton.className = "delete-btn";
              removeButton.type = "button";
              removeButton.textContent = "Remove";
              removeButton.setAttribute("aria-label", `Unregister ${email}`);
              removeButton.addEventListener("click", () =>
                handleUnregister(name, email)
              );
              participantItem.appendChild(removeButton);
            }

            participantsList.appendChild(participantItem);
          });
          participantsSection.appendChild(participantsList);
        } else {
          const emptyParticipants = document.createElement("p");
          const emptyMessage = document.createElement("em");
          emptyMessage.textContent = "No participants yet";
          emptyParticipants.appendChild(emptyMessage);
          participantsSection.appendChild(emptyParticipants);
        }

        participantsContainer.appendChild(participantsSection);
        activityCard.appendChild(participantsContainer);

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(activity, email) {
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
        if (response.status === 401) {
          updateAuthControls(null);
          fetchActivities();
        }
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
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

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
        if (response.status === 401) {
          updateAuthControls(null);
          fetchActivities();
        }
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  loginToggle.addEventListener("click", () => {
    const isExpanded = loginToggle.getAttribute("aria-expanded") === "true";
    loginForm.classList.toggle("hidden", isExpanded);
    loginToggle.setAttribute("aria-expanded", String(!isExpanded));
    if (!isExpanded) {
      document.getElementById("username").focus();
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        showMessage(result.detail || "Unable to log in.", "error");
        return;
      }

      loginForm.reset();
      updateAuthControls(result.username);
      showMessage("Teacher login successful.", "success");
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to log in. Please try again.", "error");
      console.error("Error logging in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error(`Logout request failed with status ${response.status}`);
      }
      updateAuthControls(null);
      showMessage("Logged out.", "success");
      await fetchActivities();
    } catch (error) {
      showMessage("Failed to log out. Please try again.", "error");
      console.error("Error logging out:", error);
    }
  });

  // Initialize app
  async function initialize() {
    try {
      const response = await fetch("/auth/session");
      if (!response.ok) {
        throw new Error(`Session request failed with status ${response.status}`);
      }
      const session = await response.json();
      updateAuthControls(session.authenticated ? session.username : null);
    } catch (error) {
      console.error("Error checking teacher session:", error);
      updateAuthControls(null);
    }
    await fetchActivities();
  }

  initialize();
});
