(() => {
  const list = document.querySelector("#question-list");
  const template = document.querySelector("#question-template");
  const addButton = document.querySelector("#add-question");
  const countLabel = document.querySelector("#question-count");
  const maximum = 10;

  if (!list || !template || !addButton || !countLabel) return;

  const refresh = () => {
    const cards = [...list.querySelectorAll(".question-card")];
    cards.forEach((card, index) => {
      card.querySelector(".question-number").textContent = `Question ${index + 1}`;
      card.querySelector(".remove-question").disabled = cards.length === 1;
    });
    countLabel.textContent = `${cards.length} / ${maximum} questions`;
    addButton.disabled = cards.length >= maximum;
  };

  addButton.addEventListener("click", () => {
    if (list.querySelectorAll(".question-card").length >= maximum) return;
    list.append(template.content.cloneNode(true));
    refresh();
    list.lastElementChild.querySelector("input").focus();
  });

  list.addEventListener("click", (event) => {
    const removeButton = event.target.closest(".remove-question");
    if (!removeButton || list.querySelectorAll(".question-card").length <= 1) return;
    removeButton.closest(".question-card").remove();
    refresh();
  });

  refresh();
})();
