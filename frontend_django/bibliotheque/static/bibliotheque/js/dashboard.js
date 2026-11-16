(() => {
    const root = document.documentElement;
    const body = document.body;
    const themeButtons = document.querySelectorAll(".theme-toggle");
    const storedTheme = localStorage.getItem("bibliotheque-theme");
    root.dataset.theme = storedTheme === "light" ? "light" : "dark";

    const updateThemeButton = () => {
        const isDark = root.dataset.theme === "dark";
        themeButtons.forEach((button) => {
            const hasLabel = Boolean(button.closest(".panel"));
            button.setAttribute(
                "aria-label",
                isDark ? "Passer au thème clair" : "Passer au thème sombre",
            );
            button.innerHTML = `<i class="bi ${isDark ? "bi-sun" : "bi-moon-stars"}${hasLabel ? " me-2" : ""}"></i>${hasLabel ? "Changer de thème" : ""}`;
        });
    };

    themeButtons.forEach((button) => button.addEventListener("click", () => {
        root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
        localStorage.setItem("bibliotheque-theme", root.dataset.theme);
        updateThemeButton();
        window.dispatchEvent(new CustomEvent("bibliotheque-theme-change"));
    }));
    updateThemeButton();

    document.querySelector(".sidebar-toggle")?.addEventListener("click", (event) => {
        body.classList.toggle("sidebar-collapsed");
        event.currentTarget.setAttribute(
            "aria-label",
            body.classList.contains("sidebar-collapsed")
                ? "Déployer le menu"
                : "Rétracter le menu",
        );
    });
    document.querySelector(".mobile-menu")?.addEventListener("click", () => {
        body.classList.add("sidebar-open");
    });
    document.querySelector("[data-sidebar-close]")?.addEventListener("click", () => {
        body.classList.remove("sidebar-open");
    });

    document.querySelectorAll("[data-new-entry-select]").forEach((select) => {
        const target = document.querySelector(
            `[data-new-entry="${select.dataset.newEntryTarget}"]`,
        );
        const input = target?.querySelector("input");
        if (!target || !input) return;

        const updateNewEntryVisibility = () => {
            const isCreating = select.value === "__new__";
            target.classList.toggle("d-none", !isCreating);
            input.required = isCreating;
            if (isCreating) input.focus();
        };

        select.addEventListener("change", updateNewEntryVisibility);
        updateNewEntryVisibility();
    });

})();
