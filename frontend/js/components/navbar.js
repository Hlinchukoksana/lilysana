/**
 * Bottom navigation bar controller.
 */
const Navbar = {
  init() {
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = btn.dataset.page;
        Router.navigate(page);
      });
    });
  },

  setActive(page) {
    document.querySelectorAll('.nav-item').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.page === page);
    });
  },

  updateModuleVisibility(modules) {
    const nmtBtn = document.getElementById('nav-nmt');
    const coursesBtn = document.getElementById('nav-courses');
    if (nmtBtn) nmtBtn.style.display = modules.nmt_enabled ? '' : 'none';
    if (coursesBtn) coursesBtn.style.display = modules.courses_enabled ? '' : 'none';
  }
};

window.Navbar = Navbar;
