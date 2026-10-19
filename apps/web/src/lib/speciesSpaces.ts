// Where the trace spaces of a species board are on its picture (777 x 1415 px): for each colour, the centre of its spaces from the top down, in the order of
// the engine's data (`alien-boards.json`: the k-th space of a colour column is the k-th from the top). Measured on the pictures; a space with no place here
// (the sample spaces of the Mascamites) is chosen with a button instead.
export const SPECIES_SPACES: Record<string, Record<string, ([number, number] | null)[]>> = {
  anomalies: {
    pink: [
      [142, 591],
      [142, 717],
      [142, 879],
      [142, 1036],
      [142, 1195],
    ],
    yellow: [
      [385, 664],
      [385, 793],
      [385, 947],
      [385, 1106],
      [385, 1259],
    ],
    blue: [
      [626, 591],
      [626, 717],
      [626, 879],
      [626, 1036],
      [626, 1195],
    ],
  },
  centaurians: {
    pink: [
      [142, 586],
      [142, 712],
      [142, 871],
      [142, 1026],
      [142, 1185],
    ],
    yellow: [
      [385, 659],
      [385, 785],
      [385, 939],
      [385, 1101],
      [385, 1255],
    ],
    blue: [
      [628, 586],
      [628, 712],
      [628, 871],
      [628, 1025],
      [628, 1183],
    ],
  },
  exertians: {
    pink: [
      [143, 513],
      [143, 692],
      [143, 848],
      [143, 1026],
      [143, 1193],
    ],
    yellow: [
      [388, 569],
      [388, 750],
      [388, 910],
      [388, 1078],
      [388, 1262],
    ],
    blue: [
      [628, 510],
      [628, 688],
      [628, 843],
      [628, 1032],
      [628, 1188],
    ],
  },
  oumuamua: {
    pink: [
      [146, 667],
      [146, 774],
      [146, 903],
      [146, 1044],
      [146, 1187],
    ],
    yellow: [
      [385, 738],
      [385, 842],
      [385, 979],
      [385, 1120],
      [385, 1259],
    ],
    blue: [
      [628, 667],
      [628, 774],
      [628, 903],
      [628, 1044],
      [628, 1187],
    ],
  },
  mascamites: {
    pink: [
      [137, 676],
      [137, 847],
      [137, 995],
      [137, 1150],
    ],
    yellow: [
      [373, 769],
      [373, 917],
      [373, 1072],
      [373, 1212],
    ],
    blue: [null, null, [606, 995], [606, 1150]],
  },
  arkhos: {
    pink: [
      [160, 550],
      [160, 761],
      [160, 951],
      [160, 1163],
    ],
    yellow: [
      [388, 597],
      [388, 817],
      [388, 1019],
      [388, 1234],
    ],
    blue: [
      [614, 558],
      [614, 762],
      [614, 951],
      [614, 1163],
    ],
  },
  glyphids: {
    pink: [
      [148, 655],
      [148, 815],
      [148, 945],
      [148, 1195],
    ],
    yellow: [
      [390, 745],
      [390, 880],
      [390, 1010],
      [390, 1255],
    ],
    blue: [
      [630, 655],
      [630, 815],
      [630, 945],
      [630, 1195],
    ],
  },
  amoeba: {
    pink: [
      [156, 778],
      [156, 917],
      [156, 1048],
      [156, 1185],
    ],
    yellow: [
      [389, 843],
      [389, 973],
      [389, 1113],
      [389, 1252],
    ],
    blue: [
      [621, 778],
      [621, 922],
      [621, 1048],
      [621, 1185],
    ],
  },
};

/**
 * The seven sample spaces of the Mascamites board on its picture (777 x 1415): the k-th is the k-th space of `extra.sample_spaces`. Space 0 is the printed
 * space where the first face-up token starts; 1 to 6 are the six dedicated blue spaces in the order the owner confirmed (A-056, zig-zag from the top right).
 */
export const MASCAMITE_SAMPLE_SPACES: [number, number][] = [
  [628, 872],
  [628, 390],
  [488, 465],
  [347, 542],
  [628, 555],
  [488, 628],
  [628, 713],
];
