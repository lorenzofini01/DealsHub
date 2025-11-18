FROM node:20

WORKDIR /app

# Copia package.json e package-lock.json e installa dipendenze
COPY package*.json ./
RUN npm install

# Copia tutto il frontend
COPY . .

# Espone la porta del dev server React/Vite
EXPOSE 3000

# Comando di avvio
CMD ["npm", "run", "dev"]
