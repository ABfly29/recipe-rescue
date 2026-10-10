export type Ingredient = { id: string; en: string; hi: string; emoji: string }

export type Recipe = {
  id: number
  name: string
  image: string
  time: string
  difficulty: 'Easy' | 'Medium'
  ingredients: string[] // ingredient ids
}

export const ingredients: Ingredient[] = [
  { id: 'onion', en: 'Onion', hi: 'प्याज़', emoji: '🧅' },
  { id: 'tomato', en: 'Tomato', hi: 'टमाटर', emoji: '🍅' },
  { id: 'potato', en: 'Potato', hi: 'आलू', emoji: '🥔' },
  { id: 'paneer', en: 'Paneer', hi: 'पनीर', emoji: '🧀' },
  { id: 'rice', en: 'Rice', hi: 'चावल', emoji: '🍚' },
  { id: 'dal', en: 'Lentils', hi: 'दाल', emoji: '🫘' },
  { id: 'spinach', en: 'Spinach', hi: 'पालक', emoji: '🥬' },
  { id: 'chickpeas', en: 'Chickpeas', hi: 'छोले', emoji: '🥣' },
  { id: 'cauliflower', en: 'Cauliflower', hi: 'गोभी', emoji: '🥦' },
  { id: 'peas', en: 'Green Peas', hi: 'मटर', emoji: '🟢' },
  { id: 'curd', en: 'Curd', hi: 'दही', emoji: '🥛' },
  { id: 'ginger', en: 'Ginger', hi: 'अदरक', emoji: '🫚' },
]

const img = (id: string) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=600&q=70`

// Images are hosted on Unsplash; RecipeCard shows an emoji if one fails to load.
export const recipes: Recipe[] = [
  { id: 1, name: 'Aloo Matar', image: img('photo-1585937421612-70a008356fbe'), time: '30 min', difficulty: 'Easy', ingredients: ['potato', 'peas', 'onion', 'tomato'] },
  { id: 2, name: 'Palak Paneer', image: img('photo-1618449840665-9ed506d73a34'), time: '35 min', difficulty: 'Medium', ingredients: ['spinach', 'paneer', 'onion', 'tomato', 'ginger'] },
  { id: 3, name: 'Dal Tadka', image: img('photo-1546833999-b9f581a1996d'), time: '40 min', difficulty: 'Easy', ingredients: ['dal', 'onion', 'tomato', 'ginger'] },
  { id: 4, name: 'Chole Masala', image: img('photo-1631452180519-c014fe946bc7'), time: '50 min', difficulty: 'Medium', ingredients: ['chickpeas', 'onion', 'tomato', 'ginger'] },
  { id: 5, name: 'Paneer Butter Masala', image: img('photo-1631452180775-6a1d5d3f1c6b'), time: '35 min', difficulty: 'Medium', ingredients: ['paneer', 'tomato', 'onion'] },
  { id: 6, name: 'Gobi Aloo', image: img('photo-1606491956689-2ea866880c84'), time: '30 min', difficulty: 'Easy', ingredients: ['cauliflower', 'potato', 'onion', 'tomato'] },
  { id: 7, name: 'Vegetable Pulao', image: img('photo-1596797038530-2c107229654b'), time: '35 min', difficulty: 'Easy', ingredients: ['rice', 'peas', 'onion', 'potato'] },
  { id: 8, name: 'Jeera Rice & Raita', image: img('photo-1516714435131-44d6b64dc6a2'), time: '25 min', difficulty: 'Easy', ingredients: ['rice', 'curd'] },
]
