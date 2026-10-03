// The two v1 contracts. Positions come from world.json (glTF coords: x east, y up, z = -north).
export function contracts(lq) {
  const tb = lq.toll_bridge;
  const cafe = lq.cafe;
  return [
    {
      id: 1, zh: "碼頭稅吏", en: "The Toll Collector",
      brief: ["He collects the Iron Sail's canal toll on the humpback bridge at noon.",
        "Tutorial contract: calm wind, a slow route, two bodyguards."],
      briefZh: "鐵帆會收橋稅的人，正午在拱橋上來回收錢。風小，路線慢。",
      clues: [["Coat 外套", "crimson 緋紅"], ["Hat 帽", "black tricorn 黑三角帽"], ["Guards 保鑣", "2, slate grey 石板灰"],
        ["Route 路線", "walks the toll bridge end to end 橋上來回"]],
      wind: [0.15, 0, 0.75],
      look: { coat: "#a3192b", hat: "tricorn", hatColor: "#141414", height: 1.04 },
      guardLook: { coat: "#3e4650", hat: "cap", hatColor: "#2a2f36", height: 1.05 },
      speed: 0.9,
      route: [
        { p: tb.south, wait: 7, face: 0 },
        { p: tb.center, wait: 3 },
        { p: tb.north, wait: 7, face: Math.PI },
        { p: tb.center, wait: 3 },
      ],
      bodyguards: [{ off: [0.45, 1.5] }, { off: [-0.45, -1.5] }],
      exits: [{ via: tb.south, exit: [30, 0, -1.6] }, { via: tb.north, exit: [100, 0, -9.9] }],
      awning: false,
    },
    {
      id: 2, zh: "帳房", en: "The Bookkeeper",
      brief: ["She keeps the syndicate's ledgers at a quayside café, behind a wind awning.",
        "The awning lifts in the gusts: shoot only when it is up. Strong crosswind."],
      briefZh: "鐵帆會的帳房，在碼頭咖啡館的遮篷後面算帳。陣風掀起遮篷時才有射擊窗口，橫風強。",
      clues: [["Coat 外套", "bottle green 墨綠"], ["Hat 帽", "ochre bonnet 赭黃軟帽"], ["Guards 保鑣", "2, slate grey 石板灰"],
        ["Route 路線", "sits at the café, walks to the counter 坐咖啡座、走去櫃台"]],
      wind: [-1.2, 0, 3.8],
      look: { coat: "#1f5a3c", hat: "bonnet", hatColor: "#c9962c", height: 0.98 },
      guardLook: { coat: "#3e4650", hat: "cap", hatColor: "#2a2f36", height: 1.05 },
      speed: 0.8,
      route: [
        { p: cafe.tables[0], wait: 16, seated: true, face: Math.PI / 2 },
        { p: cafe.counter, wait: 5 },
      ],
      bodyguards: [{ off: [0, 0], fixed: [49.0, 0, -2.7] }, { off: [0, 0], fixed: [52.3, 0, 0.1] }],
      exits: [{ via: cafe.tables[0], exit: [30, 0, -1.6] }],
      awning: true,
    },
  ];
}
