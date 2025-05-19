"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Download, CheckCircle2, Package } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { loadStripe } from "@stripe/stripe-js"
import { createCheckoutSession } from "@/lib/api"
import { useSearchParams, useRouter } from "next/navigation"

interface PremiumFontPackageProps {
  jobId: string | null
  fontName?: string
  onPurchaseComplete?: () => void
  isPurchased?: boolean
}

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

export default function PremiumFontPackage({
  jobId,
  fontName = "Your Custom Font",
  onPurchaseComplete,
  isPurchased: propIsPurchased = false,
}: PremiumFontPackageProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [isPurchased, setIsPurchased] = useState(propIsPurchased)
  const { toast } = useToast()
  const searchParams = useSearchParams()
  const router = useRouter()

  const [showDownloadButton, setShowDownloadButton] = useState(false)

  // Check if the user has already purchased this font
  useEffect(() => {
    // Check localStorage for purchase status
    const purchaseStatus = localStorage.getItem(`font-purchased-${jobId}`)
    if (purchaseStatus === "true" || propIsPurchased) {
      setIsPurchased(true)
    }
  }, [jobId, propIsPurchased])

  useEffect(() => {
    const checkoutStatus = searchParams.get("checkout")
    if (checkoutStatus === "success") {
      // Show toast and download button, but do NOT auto-download or redirect away
      toast({ title: "Payment Successful!", description: "Thank you for your purchase." })
      setIsPurchased(true)
      setShowDownloadButton(true)
      if (onPurchaseComplete) onPurchaseComplete()
      // Remove only the checkout param, keep jobId and others
      const params = new URLSearchParams(window.location.search);
      params.delete("checkout");
      router.replace(window.location.pathname + (params.toString() ? `?${params}` : ""), { scroll: false });
    } else if (checkoutStatus === "cancel") {
      toast({ title: "Payment Canceled", description: "You can try again at any time." })
      // Remove only the checkout param, keep jobId and others
      const params = new URLSearchParams(window.location.search);
      params.delete("checkout");
      router.replace(window.location.pathname + (params.toString() ? `?${params}` : ""), { scroll: false });
    }
  }, [searchParams, toast, router, onPurchaseComplete])

  const API_BASE = process.env.NEXT_PUBLIC_FONT_API_URL ?? ""; // Set this in your .env file for production

  const handleDownload = async () => {
    if (!jobId) {
      toast({
        title: "Error",
        description: "No font available to download.",
        variant: "destructive",
      })
      return
    }

    // If not purchased, redirect to purchase flow
    if (!isPurchased) {
      handleStripePurchase()
      return
    }

    try {
      // Use the correct ZIP download endpoint
      const downloadUrl = `${API_BASE}/download-font/${jobId}/zipped-fonts`

      // Open the download in a new tab
      window.open(downloadUrl, "_blank")

      toast({
        title: "Download Started",
        description: "Your premium font package is being downloaded.",
      })
    } catch (error) {
      console.error("Download error:", error)
      toast({
        title: "Download Error",
        description: "There was a problem downloading your font package. Please try again.",
        variant: "destructive",
      })
    }
  }

  const handleStripePurchase = async () => {
    if (!jobId) {
      toast({
        title: "Error",
        description: "No font available to purchase. Please generate a font first.",
        variant: "destructive",
      });
      return;
    }

    setIsLoading(true);
    try {
      const returnUrl = window.location.href;
      const { sessionId } = await createCheckoutSession(jobId, returnUrl);
      console.log("Stripe sessionId:", sessionId);
      const stripe = await stripePromise;
      if (stripe) {
        const { error } = await stripe.redirectToCheckout({ sessionId });
        if (error) {
          throw error;
        }
      } else {
        throw new Error("Stripe failed to load");
      }
    } catch (error: any) {
      toast({
        title: "Stripe Error",
        description: error.message || "There was a problem starting the checkout.",
        variant: "destructive",
      });
      setIsLoading(false);
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center">
          <Package className="mr-2 h-5 w-5" />
          Premium Font Package
          <Badge variant="outline" className="ml-2 bg-primary/10">
            $25
          </Badge>
        </CardTitle>
        <CardDescription>Get the complete font package with all weights from 100 to 900</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center">
            <CheckCircle2 className="h-4 w-4 mr-2 text-green-500" />
            <span>9 font weights (100-900)</span>
          </div>
          <div className="flex items-center">
            <CheckCircle2 className="h-4 w-4 mr-2 text-green-500" />
            <span>TTF, OTF & WOFF2 formats</span>
          </div>
          <div className="flex items-center">
            <CheckCircle2 className="h-4 w-4 mr-2 text-green-500" />
            <span>Commercial license</span>
          </div>
          <div className="flex items-center">
            <CheckCircle2 className="h-4 w-4 mr-2 text-green-500" />
            <span>Web font kit (WOFF, WOFF2)</span>
          </div>
          <div className="flex items-center">
            <CheckCircle2 className="h-4 w-4 mr-2 text-green-500" />
            <span>Priority email support</span>
          </div>
        </div>
      </CardContent>
      <CardFooter>
        {showDownloadButton ? (
          <Button
            onClick={handleDownload}
            disabled={!jobId}
            className="w-full"
          >
            <Download className="mr-2 h-4 w-4" />
            Download Your Premium Font Package
          </Button>
        ) : (
          <Button
            onClick={isPurchased ? handleDownload : handleStripePurchase}
            disabled={isLoading || !jobId}
            className="w-full"
          >
            {isLoading ? (
              "Processing..."
            ) : isPurchased ? (
              <>
                <Download className="mr-2 h-4 w-4" />
                Download Complete Package
              </>
            ) : (
              <>
                <Package className="mr-2 h-4 w-4" />
                Purchase ($25)
              </>
            )}
          </Button>
        )}
      </CardFooter>
    </Card>
  )
}