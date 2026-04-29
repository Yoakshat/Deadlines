export const metadata = { title: 'UW Agent' }
export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{ margin: 0, background: '#f9f9f7', minHeight: '100vh' }}>
        {children}
      </body>
    </html>
  )
}
