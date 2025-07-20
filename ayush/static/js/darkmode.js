document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("darkToggle");
    if (toggle) {
        toggle.addEventListener("click", () => {
            document.body.classList.toggle("dark");
        });
    }
});
