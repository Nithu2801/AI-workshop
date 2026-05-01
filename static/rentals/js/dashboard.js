(function () {
    const body = document.body;
    const sidebarToggle = document.querySelector("[data-sidebar-toggle]");
    const sidebarClose = document.querySelector("[data-sidebar-close]");
    const notificationToggle = document.getElementById("notificationToggle");
    const notificationClose = document.getElementById("notificationClose");
    const notificationDrawer = document.getElementById("notificationDrawer");
    const notificationOverlay = document.getElementById("notificationOverlay");

    function openNotifications() {
        notificationDrawer?.classList.add("open");
        notificationOverlay?.classList.add("open");
    }

    function closeNotifications() {
        notificationDrawer?.classList.remove("open");
        notificationOverlay?.classList.remove("open");
    }

    sidebarToggle?.addEventListener("click", function () {
        body.classList.add("sidebar-open");
    });

    sidebarClose?.addEventListener("click", function () {
        body.classList.remove("sidebar-open");
    });

    notificationToggle?.addEventListener("click", openNotifications);
    notificationClose?.addEventListener("click", closeNotifications);
    notificationOverlay?.addEventListener("click", closeNotifications);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            body.classList.remove("sidebar-open");
            closeNotifications();
        }
    });
})();
