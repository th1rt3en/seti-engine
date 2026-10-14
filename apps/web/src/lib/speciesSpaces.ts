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
      [113, 513],
      [113, 688],
      [113, 842],
      [113, 1023],
      [113, 1190],
    ],
    yellow: [
      [372, 570],
      [372, 712],
      [372, 874],
      [372, 1052],
      [372, 1225],
    ],
    blue: [
      [626, 513],
      [626, 656],
      [626, 809],
      [626, 996],
      [626, 1154],
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
};
